"""
AiSensy webhook integration for automatic inbound WhatsApp lead creation/update.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _digits_phone(s: Any, max_len: int = 15) -> str:
    d = re.sub(r"\D", "", str(s or ""))
    return d[-max_len:] if len(d) > max_len else d


def _clean_text(s: Any, max_len: int = 2000) -> str:
    return str(s or "").strip()[:max_len]


def _placeholder_email(phone_digits: str) -> str:
    # Keep email valid and deterministic for records created from WhatsApp only.
    token = (phone_digits or "unknown")[:40]
    return f"aisensy.{token}@example.com"


def effective_aisensy_config() -> Dict[str, Any]:
    from .models import AiSensyIntegrationSettings

    s = AiSensyIntegrationSettings.get_solo()
    return {
        "enabled": bool(s.enabled),
        "public_base_url": (s.public_base_url or "").strip().rstrip("/"),
        "webhook_secret": _env("AISENSY_WEBHOOK_SECRET") or (s.webhook_secret or "").strip(),
        "webhook_token": _env("AISENSY_WEBHOOK_TOKEN") or (s.webhook_token or "").strip(),
    }


def _ensure_lead_source(name: str = "AiSensy WhatsApp"):
    from .models import LeadSource

    src, _ = LeadSource.objects.get_or_create(
        name=name,
        defaults={"description": "Inbound leads from AiSensy webhook", "is_active": True},
    )
    return src


def _extract_signature_header(headers: Dict[str, str]) -> str:
    return (
        headers.get("HTTP_X_AISENSY_SIGNATURE")
        or headers.get("HTTP_X_AISENSY_WEBHOOK_SIGNATURE")
        or headers.get("HTTP_X_WEBHOOK_SIGNATURE")
        or ""
    ).strip()


def _verify_hmac_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
    if not secret:
        return False
    if not signature_header:
        return False
    sig = signature_header
    if sig.startswith("sha256="):
        sig = sig[7:]
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _verify_token(headers: Dict[str, str], expected_token: str) -> bool:
    if not expected_token:
        return False

    auth = (headers.get("HTTP_AUTHORIZATION") or "").strip()
    if auth.lower().startswith("bearer "):
        bearer = auth[7:].strip()
        if hmac.compare_digest(bearer, expected_token):
            return True

    for key in (
        "HTTP_X_AISENSY_TOKEN",
        "HTTP_X_AISENSY_WEBHOOK_TOKEN",
        "HTTP_X_API_KEY",
    ):
        val = (headers.get(key) or "").strip()
        if val and hmac.compare_digest(val, expected_token):
            return True
    return False


def authorize_aisensy_webhook(raw_body: bytes, headers: Dict[str, str]) -> bool:
    """
    Authorization strategy:
    1) If AISENSY_WEBHOOK_SECRET is configured, require valid HMAC signature.
    2) Else if AISENSY_WEBHOOK_TOKEN is configured, require bearer/token header match.
    3) Else reject (production-safe default).
    """
    cfg = effective_aisensy_config()
    if not cfg.get("enabled", True):
        logger.warning("AiSensy webhook rejected: integration disabled")
        return False

    secret = cfg.get("webhook_secret") or ""
    token = cfg.get("webhook_token") or ""

    if secret:
        sig_header = _extract_signature_header(headers)
        return _verify_hmac_signature(raw_body, sig_header, secret)

    if token:
        return _verify_token(headers, token)

    logger.error(
        "AiSensy webhook auth rejected: no AISENSY_WEBHOOK_SECRET or AISENSY_WEBHOOK_TOKEN configured."
    )
    return False


def _iter_dict_candidates(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """
    Yield likely event/message dictionaries from varied webhook payload shapes.
    """
    yield payload

    if isinstance(payload.get("data"), dict):
        yield payload["data"]
    if isinstance(payload.get("message"), dict):
        yield payload["message"]

    msgs = payload.get("messages")
    if isinstance(msgs, list):
        for m in msgs:
            if isinstance(m, dict):
                yield m

    events = payload.get("events")
    if isinstance(events, list):
        for ev in events:
            if isinstance(ev, dict):
                yield ev
                if isinstance(ev.get("message"), dict):
                    yield ev["message"]
                if isinstance(ev.get("data"), dict):
                    yield ev["data"]


def _first_non_empty(*values: Any) -> str:
    for v in values:
        txt = str(v or "").strip()
        if txt:
            return txt
    return ""


def parse_aisensy_messages(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Parse inbound webhook payload into normalized message records.
    """
    records: List[Dict[str, str]] = []
    for obj in _iter_dict_candidates(payload):
        direction = _first_non_empty(obj.get("direction"), obj.get("message_direction")).lower()
        if direction and direction in {"outgoing", "sent"}:
            continue

        phone = _first_non_empty(
            obj.get("phone"),
            obj.get("phone_number"),
            obj.get("mobile"),
            obj.get("wa_id"),
            obj.get("from"),
            (obj.get("contact") or {}).get("phone") if isinstance(obj.get("contact"), dict) else "",
            (obj.get("sender") or {}).get("phone") if isinstance(obj.get("sender"), dict) else "",
            (obj.get("sender") or {}).get("wa_id") if isinstance(obj.get("sender"), dict) else "",
        )
        phone_digits = _digits_phone(phone)
        if not phone_digits:
            continue

        text = _first_non_empty(
            obj.get("message"),
            obj.get("text"),
            obj.get("body"),
            (obj.get("content") or {}).get("text") if isinstance(obj.get("content"), dict) else "",
            (obj.get("message") or {}).get("text") if isinstance(obj.get("message"), dict) else "",
        )
        if not text:
            # Non-text events (delivery/read) should not create leads.
            continue

        name = _first_non_empty(
            obj.get("name"),
            obj.get("sender_name"),
            (obj.get("contact") or {}).get("name") if isinstance(obj.get("contact"), dict) else "",
            (obj.get("sender") or {}).get("name") if isinstance(obj.get("sender"), dict) else "",
        ) or "WhatsApp User"

        email = _first_non_empty(
            obj.get("email"),
            (obj.get("contact") or {}).get("email") if isinstance(obj.get("contact"), dict) else "",
            (obj.get("sender") or {}).get("email") if isinstance(obj.get("sender"), dict) else "",
        )

        msg_id = _first_non_empty(obj.get("message_id"), obj.get("id"), obj.get("wamid"))

        records.append(
            {
                "phone": phone_digits,
                "name": _clean_text(name, 200),
                "email": _clean_text(email, 254),
                "text": _clean_text(text, 2000),
                "message_id": _clean_text(msg_id, 128),
            }
        )
    return records


def _append_note(lead, line: str) -> None:
    line = _clean_text(line, 2000)
    if not line:
        return
    prev = (lead.notes or "").strip()
    lead.notes = f"{prev}\n{line}".strip() if prev else line


def upsert_lead_from_aisensy(record: Dict[str, str]) -> Dict[str, Any]:
    """
    Dedupe/update order:
    - phone (primary)
    - email (if provided)
    """
    from .models import Lead

    source = _ensure_lead_source()
    phone = record["phone"]
    email = (record.get("email") or "").strip().lower()
    text = record.get("text") or ""
    display_name = (record.get("name") or "WhatsApp User").strip()

    with transaction.atomic():
        lead = (
            Lead.objects.select_for_update()
            .filter(phone=phone)
            .order_by("-updated_at", "-created_at")
            .first()
        )
        if lead is None and email:
            lead = (
                Lead.objects.select_for_update()
                .filter(email__iexact=email)
                .order_by("-updated_at", "-created_at")
                .first()
            )

        created = False
        if lead is None:
            parts = display_name.split(None, 1)
            first_name = (parts[0] if parts else "WhatsApp")[:100]
            last_name = (parts[1] if len(parts) > 1 else "Lead")[:100]
            lead = Lead(
                first_name=first_name,
                last_name=last_name,
                email=email or _placeholder_email(phone),
                phone=phone,
                source=source,
                status="NEW",
                notes="",
            )
            created = True
        else:
            if created is False and email and (lead.email or "").endswith("@example.com"):
                lead.email = email
            if not lead.source_id:
                lead.source = source

        note_line = f"[AiSensy] {text}"
        _append_note(lead, note_line)
        lead.save()

    return {"lead_id": lead.id, "lead_code": lead.lead_id, "created": created}


def process_aisensy_webhook(raw_body: bytes) -> Dict[str, Any]:
    """
    Parse payload, upsert leads, and return processing summary.
    """
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "error": "invalid_json"}

    records = parse_aisensy_messages(payload)
    created = 0
    updated = 0
    processed = 0
    errors = 0

    for record in records:
        try:
            out = upsert_lead_from_aisensy(record)
            processed += 1
            if out.get("created"):
                created += 1
                logger.info(
                    "AiSensy lead created lead_id=%s phone=%s msg_id=%s",
                    out.get("lead_code"),
                    record.get("phone"),
                    record.get("message_id"),
                )
            else:
                updated += 1
                logger.info(
                    "AiSensy lead updated lead_id=%s phone=%s msg_id=%s",
                    out.get("lead_code"),
                    record.get("phone"),
                    record.get("message_id"),
                )
        except Exception:
            errors += 1
            logger.exception(
                "AiSensy lead upsert failed phone=%s msg_id=%s",
                record.get("phone"),
                record.get("message_id"),
            )

    logger.info(
        "AiSensy webhook processed at=%s records=%s created=%s updated=%s errors=%s",
        timezone.now().isoformat(),
        len(records),
        created,
        updated,
        errors,
    )
    return {
        "ok": True,
        "records": len(records),
        "processed": processed,
        "created": created,
        "updated": updated,
        "errors": errors,
    }
