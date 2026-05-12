from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0028_aisensyintegrationsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='counsellor',
            name='can_create_own_leads',
            field=models.BooleanField(
                default=False,
                help_text='When enabled, this counsellor may add a single new lead from My Leads.',
            ),
        ),
    ]
