from django.db import migrations


def seed_achievements(apps, schema_editor):
    Achievement = apps.get_model('achievements', 'Achievement')

    achievements_data = [
        ('First Step', '✅', 'TASKS_COMPLETED', 1, 20),
        ('Getting Things Done', '📝', 'TASKS_COMPLETED', 5, 30),
        ('Task Master', '💯', 'TASKS_COMPLETED', 25, 75),

        ('3-Day Streak', '🔥', 'STREAK', 3, 25),
        ('7-Day Streak', '🔥', 'STREAK', 7, 50),
        ('30-Day Streak', '🏆', 'STREAK', 30, 150),

        ('First Focus Session', '🍅', 'FOCUS_HOURS', 1, 20),
        ('10 Focus Hours', '⏳', 'FOCUS_HOURS', 10, 60),
        ('50 Focus Hours', '🧠', 'FOCUS_HOURS', 50, 150),

        ('First Study Session', '📖', 'STUDY_SESSIONS', 1, 20),
        ('10 Study Sessions', '📚', 'STUDY_SESSIONS', 10, 60),

        ('Goal Achiever', '🎯', 'GOALS_COMPLETED', 1, 50),
        ('Goal Crusher', '🏅', 'GOALS_COMPLETED', 5, 150),
    ]

    for name, icon, criteria_type, criteria_value, xp_reward in achievements_data:
        Achievement.objects.get_or_create(
            name=name,
            defaults={
                'icon': icon,
                'criteria_type': criteria_type,
                'criteria_value': criteria_value,
                'xp_reward': xp_reward,
            }
        )


def remove_achievements(apps, schema_editor):
    Achievement = apps.get_model('achievements', 'Achievement')
    Achievement.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0002_alter_achievement_xp_reward'),
    ]

    operations = [
        migrations.RunPython(seed_achievements, remove_achievements),
    ]