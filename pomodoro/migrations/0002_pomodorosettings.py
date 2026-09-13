from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pomodoro', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PomodoroSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('daily_goal', models.PositiveSmallIntegerField(default=6, validators=[MinValueValidator(1), MaxValueValidator(20)])),
                ('user', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='pomodoro_settings', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
