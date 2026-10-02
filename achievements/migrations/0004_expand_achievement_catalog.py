from django.db import migrations


ACHIEVEMENTS = [
    ('Task Momentum', '⚡', 'TASKS_COMPLETED', 10, 50),
    ('Task Trailblazer', '🧭', 'TASKS_COMPLETED', 50, 125),
    ('Task Century', '💯', 'TASKS_COMPLETED', 100, 250),
    ('Two-Week Rhythm', '🌿', 'STREAK', 14, 75),
    ('Habit Stronghold', '🏔️', 'STREAK', 60, 200),
    ('Century of Consistency', '🌟', 'STREAK', 100, 350),
    ('Focused Five', '🍅', 'FOCUS_HOURS', 5, 50),
    ('Deep Work', '🧠', 'FOCUS_HOURS', 25, 125),
    ('Focus Centurion', '🔥', 'FOCUS_HOURS', 100, 300),
    ('Study Rhythm', '📚', 'STUDY_SESSIONS', 25, 100),
    ('Study Scholar', '🎓', 'STUDY_SESSIONS', 50, 175),
    ('Learning Library', '📖', 'STUDY_SESSIONS', 100, 300),
    ('Goal Builder', '🧱', 'GOALS_COMPLETED', 10, 125),
    ('Goal Architect', '🏛️', 'GOALS_COMPLETED', 20, 250),
]


def add_achievements(apps, schema_editor):
    Achievement = apps.get_model('achievements', 'Achievement')
    for name, icon, criteria_type, criteria_value, xp_reward in ACHIEVEMENTS:
        Achievement.objects.get_or_create(
            name=name,
            defaults={
                'icon': icon,
                'criteria_type': criteria_type,
                'criteria_value': criteria_value,
                'xp_reward': xp_reward,
            },
        )


def remove_achievements(apps, schema_editor):
    Achievement = apps.get_model('achievements', 'Achievement')
    Achievement.objects.filter(name__in=[item[0] for item in ACHIEVEMENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('achievements', '0003_seed_achievements'),
    ]

    operations = [
        migrations.RunPython(add_achievements, remove_achievements),
    ]
