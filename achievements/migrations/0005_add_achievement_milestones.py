from django.db import migrations


ACHIEVEMENTS = [
    ('Task Marathon', '🏃', 'TASKS_COMPLETED', 150, 350),
    ('Task Vanguard', '🚀', 'TASKS_COMPLETED', 250, 500),
    ('Task Legacy', '👑', 'TASKS_COMPLETED', 500, 1000),
    ('Half-Year Habit', '🌱', 'STREAK', 180, 350),
    ('Consistency Champion', '🏅', 'STREAK', 250, 500),
    ('Year of Consistency', '🌟', 'STREAK', 365, 1000),
    ('Focus Veteran', '🎯', 'FOCUS_HOURS', 150, 350),
    ('Focus Elite', '⚡', 'FOCUS_HOURS', 250, 500),
    ('Focus Legend', '🧠', 'FOCUS_HOURS', 500, 1000),
    ('Study Mentor', '📘', 'STUDY_SESSIONS', 200, 350),
    ('Study Master', '🎓', 'STUDY_SESSIONS', 500, 1000),
    ('Goal Champion', '🏆', 'GOALS_COMPLETED', 30, 350),
    ('Goal Legend', '✨', 'GOALS_COMPLETED', 50, 750),
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
        ('achievements', '0004_expand_achievement_catalog'),
    ]

    operations = [
        migrations.RunPython(add_achievements, remove_achievements),
    ]
