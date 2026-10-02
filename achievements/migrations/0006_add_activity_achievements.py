from django.db import migrations, models


ACHIEVEMENTS = [
    ('First Check-In', '✅', 'HABIT_CHECKINS', 1, 15),
    ('Routine Builder', '🌿', 'HABIT_CHECKINS', 7, 30),
    ('Habit Keeper', '💚', 'HABIT_CHECKINS', 30, 75),
    ('First Milestone', '🪜', 'MILESTONES_COMPLETED', 1, 20),
    ('Milestone Momentum', '🧭', 'MILESTONES_COMPLETED', 5, 50),
    ('Milestone Finisher', '🏁', 'MILESTONES_COMPLETED', 15, 100),
    ('First Pomodoro', '🍅', 'FOCUS_SESSIONS', 1, 15),
    ('Focus Flow', '🎯', 'FOCUS_SESSIONS', 5, 40),
    ('Focus Habit', '⚡', 'FOCUS_SESSIONS', 20, 100),
    ('Study Hour', '📚', 'STUDY_MINUTES', 60, 20),
    ('Study Groove', '✍️', 'STUDY_MINUTES', 180, 50),
    ('Study Commitment', '🎓', 'STUDY_MINUTES', 600, 125),
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
        ('achievements', '0005_add_achievement_milestones'),
    ]

    operations = [
        migrations.AlterField(
            model_name='achievement',
            name='criteria_type',
            field=models.CharField(
                choices=[
                    ('STREAK', 'Habit Streak'),
                    ('TASKS_COMPLETED', 'Tasks Completed'),
                    ('FOCUS_HOURS', 'Focus Hours'),
                    ('STUDY_SESSIONS', 'Study Sessions'),
                    ('GOALS_COMPLETED', 'Goals Completed'),
                    ('HABIT_CHECKINS', 'Habit Check-ins'),
                    ('MILESTONES_COMPLETED', 'Milestones Completed'),
                    ('FOCUS_SESSIONS', 'Focus Sessions'),
                    ('STUDY_MINUTES', 'Study Time'),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(add_achievements, remove_achievements),
    ]
