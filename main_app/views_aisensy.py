import logging

from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .aisensy_services import (
    authorize_aisensy_webhook,
    effective_aisensy_config,
    process_aisensy_webhook,
)
from .forms import AiSensyIntegrationSettingsForm
from .models import AiSensyIntegrationSettings
from .utils import admin_perm_required, user_type_required

logger = logging.getLogger(__name__)
admin_required = user_type_required("1")


@csrf_exempt
@require_POST
def aisensy_webhook(request):
    """
    Public webhook endpoint for AiSensy WhatsApp events.
    Creates/updates leads from inbound messages with dedupe and logging.
    """
    raw = request.body or b""
    if not authorize_aisensy_webhook(raw, request.META):
        logger.warning("AiSensy webhook rejected: auth failed")
        return HttpResponseForbidden("Invalid webhook authentication")

    summary = process_aisensy_webhook(raw)
    if not summary.get("ok"):
        return JsonResponse(summary, status=400)
    return JsonResponse(summary, status=200)


aisensy_webhook.allow_without_login = True


@admin_required
@admin_perm_required("settings")
def manage_aisensy_integration(request):
    inst = AiSensyIntegrationSettings.get_solo()
    if request.method == "POST":
        form = AiSensyIntegrationSettingsForm(request.POST, instance=inst)
        if form.is_valid():
            form.save()
            messages.success(request, "AiSensy integration settings saved.")
            return redirect(reverse("manage_aisensy_integration"))
    else:
        form = AiSensyIntegrationSettingsForm(instance=inst)

    cfg = effective_aisensy_config()
    webhook_path = reverse("aisensy_webhook")
    base = cfg.get("public_base_url") or ""
    webhook_full = f"{base}{webhook_path}" if base else ""

    return render(
        request,
        "admin_template/manage_aisensy_integration.html",
        {
            "page_title": "AiSensy WhatsApp",
            "form": form,
            "webhook_full_url": webhook_full,
            "webhook_path": webhook_path,
            "using_env_secret": bool((cfg.get("webhook_secret") or "").strip()),
            "using_env_token": bool((cfg.get("webhook_token") or "").strip()),
            "enabled": bool(cfg.get("enabled", True)),
        },
    )
