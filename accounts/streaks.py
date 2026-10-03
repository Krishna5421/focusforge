"""Activity streak: consecutive days with at least one completed task, habit check-in,
focus session, or study session.

Streaks are recalculated from the activity itself whenever they are shown, so they stay
correct after inactivity or when a task/habit is un-checked, and need no background job.
"""
from datetime import timedelta

from django.utils import timezone

from habits.models import HabitLog
from pomodoro.models import PomodoroSession
from study.models import StudySession
from tasks.models import Task

from .models import Profile

ONE_DAY = timedelta(days=1)


def activity_dates(user):
    """Local calendar dates on which the user did something productive."""
    dates = set(Task.objects.filter(user=user, status='COMPLETED', completed_at__isnull=False)
                .values_list('completed_at__date', flat=True))
    dates |= set(HabitLog.objects.filter(habit__user=user, completed=True).values_list('date', flat=True))
    dates |= set(PomodoroSession.objects.filter(user=user, status='COMPLETED', completed_at__isnull=False)
                 .values_list('completed_at__date', flat=True))
    dates |= set(StudySession.objects.filter(user=user).values_list('date', flat=True))
    dates.discard(None)
    return dates


def calculate_streaks(dates, today):
    """Return (current, longest) streak lengths in days.

    Today does not break the streak until it is over: with no activity yet today,
    the streak that ended yesterday still counts.
    """
    day = today if today in dates else today - ONE_DAY
    current = 0
    while day in dates:
        current += 1
        day -= ONE_DAY

    longest = run = 0
    previous = None
    for day in sorted(d for d in dates if d <= today):
        run = run + 1 if previous is not None and day - previous == ONE_DAY else 1
        longest = max(longest, run)
        previous = day
    return current, max(longest, current)


def refresh_activity_streak(user, today=None):
    """Recalculate and store the user's streaks; returns their up-to-date Profile."""
    profile, _ = Profile.objects.get_or_create(user=user)
    current, longest = calculate_streaks(activity_dates(user), today or timezone.localdate())
    if (profile.current_streak, profile.longest_streak) != (current, longest):
        # Queryset update: no Profile save signals, and other profile fields are untouched.
        Profile.objects.filter(pk=profile.pk).update(current_streak=current, longest_streak=longest)
        profile.current_streak, profile.longest_streak = current, longest
    return profile
