from .models import Admin, Counsellor, NotificationAdmin, NotificationCounsellor


def notification_count(request):
    """
    Notification badge count. Do not use hasattr(user, 'counsellor'): reverse OneToOne
    raises Model.DoesNotExist (not AttributeError), which hasattr does not catch → HTTP 500.
    """
    count = 0
    if not request.user.is_authenticated:
        return {"notification_count": count}
    ut = str(getattr(request.user, "user_type", ""))
    if ut == "2":
        try:
            counsellor = request.user.counsellor
            count = NotificationCounsellor.objects.filter(
                counsellor=counsellor, is_read=False
            ).count()
        except Counsellor.DoesNotExist:
            count = 0
    if ut == "1":
        count = NotificationAdmin.objects.filter(
            admin=request.user, is_read=False
        ).count()
    return {"notification_count": count}


def pending_task_count(request):
    """Sidebar badge: incomplete activities + upcoming visits."""
    if not request.user.is_authenticated or str(getattr(request.user, "user_type", "")) != "2":
        return {}
    try:
        from .models import Counsellor, LeadActivity, Lead
        from django.utils import timezone
        counsellor = Counsellor.objects.get(admin=request.user)
        incomplete = LeadActivity.objects.filter(counsellor=counsellor, is_completed=False).count()
        upcoming_visits = Lead.objects.filter(
            assigned_counsellor=counsellor,
            next_follow_up__isnull=False,
            next_follow_up__gte=timezone.now(),
        ).count()
        return {'pending_task_count': incomplete + upcoming_visits}
    except Exception:
        return {'pending_task_count': 0}


def lead_status_info(request):
    """lead_status_map and lead_status_choices for templates."""
    from .models import LeadStatus
    try:
        statuses = LeadStatus.objects.all().order_by('sort_order', 'name')
        status_map = {s.code: {'name': s.name, 'color': s.color} for s in statuses}
        status_choices = [(s.code, s.name) for s in statuses if s.is_active]
    except Exception:
        status_map = {}
        status_choices = []
    return {
        'lead_status_map': status_map,
        'lead_status_choices': status_choices,
    }


def admin_permissions(request):
    """perm_delete, perm_performance, etc. for admin templates."""
    if not request.user.is_authenticated or str(getattr(request.user, "user_type", "")) != "1":
        return {}
    try:
        admin_obj = Admin.objects.get(admin=request.user)
        return {
            'perm_delete': admin_obj.has_perm_delete(),
            'perm_performance': admin_obj.has_perm_performance(),
            'perm_counsellor_work': admin_obj.has_perm_counsellor_work(),
            'perm_settings': admin_obj.has_perm_settings(),
            'is_superadmin': admin_obj.is_superadmin,
        }
    except Admin.DoesNotExist:
        return {}
