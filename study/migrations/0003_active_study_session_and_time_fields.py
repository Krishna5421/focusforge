import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('study', '0002_studysession_resource_name')]
    operations = [
        migrations.AddField(model_name='studysession', name='actual_seconds', field=models.IntegerField(default=0)),
        migrations.AddField(model_name='studysession', name='planned_minutes', field=models.IntegerField(default=0)),
        migrations.CreateModel(
            name='ActiveStudySession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('planned_minutes', models.IntegerField()), ('remaining_seconds', models.IntegerField()),
                ('notes', models.TextField(blank=True)), ('resource_name', models.CharField(blank=True, max_length=255)),
                ('is_running', models.BooleanField(default=False)), ('timer_started_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='active_sessions', to='study.subject')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='active_study_session', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
