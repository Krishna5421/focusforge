from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('study', '0003_active_study_session_and_time_fields')]

    operations = [
        migrations.AddField(
            model_name='studysession',
            name='resource_file',
            field=models.FileField(blank=True, null=True, upload_to='study_files/'),
        ),
        migrations.AddField(
            model_name='activestudysession',
            name='resource_file',
            field=models.FileField(blank=True, null=True, upload_to='study_files/'),
        ),
    ]
