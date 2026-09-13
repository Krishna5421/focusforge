from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('pomodoro', '0002_pomodorosettings')]
    operations = [migrations.AddField(model_name='pomodorosession', name='last_resumed_at', field=models.DateTimeField(blank=True, null=True))]
