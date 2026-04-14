"""
Invalidate admin home dashboard cache when counsellor or lead aggregates can change.

Bulk create/update paths must call invalidate_admin_dashboard_cache() explicitly
(Django does not emit post_save for those).
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Counsellor, Lead
from .utils import invalidate_admin_dashboard_cache

_LEAD_FIELDS_AFFECTING_ADMIN_DASHBOARD = frozenset(
    {"assigned_counsellor", "assigned_counsellor_id", "status"}
)


@receiver([post_save, post_delete], sender=Counsellor)
def _invalidate_admin_dashboard_on_counsellor_change(sender, **kwargs):
    invalidate_admin_dashboard_cache()


@receiver(post_delete, sender=Lead)
def _invalidate_admin_dashboard_on_lead_delete(sender, **kwargs):
    invalidate_admin_dashboard_cache()


@receiver(post_save, sender=Lead)
def _invalidate_admin_dashboard_on_lead_save(sender, instance, created, **kwargs):
    if created:
        invalidate_admin_dashboard_cache()
        return
    update_fields = kwargs.get("update_fields")
    if update_fields is None:
        invalidate_admin_dashboard_cache()
        return
    if _LEAD_FIELDS_AFFECTING_ADMIN_DASHBOARD.intersection(update_fields):
        invalidate_admin_dashboard_cache()
