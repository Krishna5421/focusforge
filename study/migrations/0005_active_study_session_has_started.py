from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('study', '0004_study_session_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='activestudysession',
            name='has_started',
            field=models.BooleanField(default=False),
        ),
    ]
