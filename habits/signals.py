from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import timedelta
from .models import HabitLog
from achievements.utils import award_xp


def recalculate_streak(habit):
    logs = habit.logs.filter(completed=True).order_by('-date')

    if not logs.exists():
        habit.current_streak = 0
        habit.save(update_fields=['current_streak'])
        return

    current_streak = 1
    dates = list(logs.values_list('date', flat=True))

    for i in range(1, len(dates)):
        if dates[i - 1] - dates[i] == timedelta(days=1):
            current_streak += 1
        else:
            break

    habit.current_streak = current_streak
    if current_streak > habit.longest_streak:
        habit.longest_streak = current_streak

    habit.save(update_fields=['current_streak', 'longest_streak'])


@receiver(post_save, sender=HabitLog)
def update_streak_on_log(sender, instance, **kwargs):
    recalculate_streak(instance.habit)

    already_awarded_today = HabitLog.objects.filter(
        habit=instance.habit, date=instance.date, xp_awarded=True
    ).exclude(pk=instance.pk).exists()

    if instance.completed and not already_awarded_today and not instance.xp_awarded:
        award_xp(instance.habit.user, 'HABIT_CHECKIN')
        HabitLog.objects.filter(pk=instance.pk).update(xp_awarded=True)


@receiver(post_delete, sender=HabitLog)
def update_streak_on_log_delete(sender, instance, **kwargs):
    recalculate_streak(instance.habit)