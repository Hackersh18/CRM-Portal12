from django.db import migrations


def seed_awaiting_response(apps, schema_editor):
    LeadStatus = apps.get_model('main_app', 'LeadStatus')
    LeadStatus.objects.get_or_create(
        code='AWAITING_RESPONSE',
        defaults={
            'name': 'Awaiting Response',
            'description': 'Waiting for the prospect to reply (e.g. activity logged with no outcome).',
            'color': 'secondary',
            'is_active': True,
            'is_system': False,
            'sort_order': 25,
        },
    )


def reverse_seed(apps, schema_editor):
    LeadStatus = apps.get_model('main_app', 'LeadStatus')
    LeadStatus.objects.filter(code='AWAITING_RESPONSE').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0029_counsellor_can_create_own_leads'),
    ]

    operations = [
        migrations.RunPython(seed_awaiting_response, reverse_seed),
    ]
