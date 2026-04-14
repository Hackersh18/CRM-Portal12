"""
Enable PostgreSQL Row Level Security on all Django-managed tables.

Supabase exposes the public schema to PostgREST (anon/authenticated). Without RLS,
those roles could read/write any granted table. Enabling RLS with no policies
denies access for non-owner roles; Django's database user is typically the table
owner or a superuser (e.g. Supabase `postgres`) and bypasses RLS.

If you use a custom DB role that is not the owner and not superuser, grant:
  ALTER ROLE your_django_role BYPASSRLS;
"""

from django.db import migrations

# Tables in public that PostgREST can see — match Django default names (lowercase).
_RLS_TABLES = (
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "django_admin_log",
    "django_content_type",
    "django_migrations",
    "django_session",
    "main_app_activitytype",
    "main_app_admin",
    "main_app_business",
    "main_app_counsellor",
    "main_app_counsellorperformance",
    "main_app_customuser",
    "main_app_customuser_groups",
    "main_app_customuser_user_permissions",
    "main_app_dailytarget",
    "main_app_dailytargetassignment",
    "main_app_dataaccesslog",
    "main_app_lead",
    "main_app_leadactivity",
    "main_app_leadalternatephone",
    "main_app_leadsource",
    "main_app_leadstatus",
    "main_app_leadtransfer",
    "main_app_metaintegrationsettings",
    "main_app_nextaction",
    "main_app_notificationadmin",
    "main_app_notificationcounsellor",
    "main_app_socialchatmessage",
    "main_app_socialchatthread",
)


def _set_rls(schema_editor, enable: bool) -> None:
    conn = schema_editor.connection
    if conn.vendor != "postgresql":
        return
    verb = "ENABLE" if enable else "DISABLE"
    with conn.cursor() as cursor:
        for table in _RLS_TABLES:
            qtable = conn.ops.quote_name(table)
            cursor.execute(
                f"ALTER TABLE IF EXISTS public.{qtable} {verb} ROW LEVEL SECURITY"
            )


def enable_rls(apps, schema_editor):
    _set_rls(schema_editor, True)


def disable_rls(apps, schema_editor):
    _set_rls(schema_editor, False)


class Migration(migrations.Migration):

    dependencies = [
        ("main_app", "0026_social_chat_inbox"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
