"""Which habits are due on a given day, and per-habit stats for the Habits page."""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.utils import dateformat, timezone

from .models import Habit, HabitLog

WEEKDAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
RATE_WINDOW_DAYS = 30


def is_scheduled_on(habit, day):
    """Daily habits and 'once a week' habits can be done any day; others only on their chosen weekdays."""
    if habit.frequency == 'WEEKLY' and habit.target_days:
        return day.isoweekday() in habit.target_days
    return True


def schedule_label(habit):
    if habit.frequency == 'DAILY':
        return 'Daily'
    if habit.target_days:
        return ', '.join(WEEKDAY_SHORT[day - 1] for day in sorted(habit.target_days))
    return 'Once a week'


def week_start(day):
    return day - timedelta(days=day.weekday())


def is_due_today(habit, today, done_dates):
    if habit.frequency == 'WEEKLY' and not habit.target_days:
        # Once a week: due until it has been done on an earlier day this week.
        return not any(week_start(today) <= day < today for day in done_dates)
    return is_scheduled_on(habit, today)


def next_scheduled_day(habit, today):
    for offset in range(1, 8):
        day = today + timedelta(days=offset)
        if is_scheduled_on(habit, day):
            return day
    return None


def expected_checkins(habit, first, last):
    if first > last:
        return 0
    days = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    if habit.frequency == 'WEEKLY':
        if habit.target_days:
            return sum(1 for day in days if day.isoweekday() in habit.target_days)
        return len({day.isocalendar()[:2] for day in days})
    return len(days)


def completion_rate(habit, done_dates, today):
    """Share of scheduled check-ins done in the last 30 days (or since the habit was created)."""
    created = timezone.localtime(habit.created_at).date()
    first = max(today - timedelta(days=RATE_WINDOW_DAYS - 1), created)
    expected = expected_checkins(habit, first, today)
    done = sum(1 for day in done_dates if first <= day <= today)
    return min(100, round(done / expected * 100)) if expected else 0


def completed_dates_by_habit(habits, since, until):
    dates = defaultdict(set)
    for habit_id, day in HabitLog.objects.filter(
        habit__in=habits, completed=True, date__range=(since, until),
    ).values_list('habit_id', 'date'):
        dates[habit_id].add(day)
    return dates


def month_summary(user, habits, today):
    """Check-ins, best day, and consistency for the current month (shown above the heatmap)."""
    month_start = today.replace(day=1)
    counts = dict(HabitLog.objects.filter(
        habit__user=user, habit__is_active=True, completed=True, date__range=(month_start, today),
    ).values('date').annotate(total=Count('id')).values_list('date', 'total'))
    checkins = sum(counts.values())
    best_day = max(sorted(counts), key=counts.get) if counts else None
    expected = sum(expected_checkins(h, max(month_start, timezone.localtime(h.created_at).date()), today) for h in habits)
    return {
        'checkins': checkins,
        'best_day': best_day,
        'best_day_label': dateformat.format(best_day, 'M j') if best_day else '—',
        'best_count': counts.get(best_day, 0),
        'consistency': min(100, round(checkins / expected * 100)) if expected else 0,
    }


def annotate_habits(user, today=None):
    """Active habits with today's status and stats attached, plus (due_done, due_total)."""
    today = today or timezone.localdate()
    habits = list(Habit.objects.filter(user=user, is_active=True))
    since = min(today - timedelta(days=RATE_WINDOW_DAYS - 1), week_start(today))
    done_by_habit = completed_dates_by_habit(habits, since, today)
    week_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]

    for habit in habits:
        done = done_by_habit[habit.pk]
        habit.completed_today = today in done
        habit.due_today = is_due_today(habit, today, done)
        habit.done_this_week = (habit.frequency == 'WEEKLY' and not habit.target_days
                                and any(week_start(today) <= day <= today for day in done))
        habit.schedule_label = schedule_label(habit)
        habit.next_day = None if habit.due_today else next_scheduled_day(habit, today)
        habit.rate = completion_rate(habit, done, today)
        habit.week = [{'date': day, 'done': day in done, 'today': day == today,
                       'scheduled': is_scheduled_on(habit, day)} for day in week_days]

    due = [habit for habit in habits if habit.due_today]
    return habits, sum(1 for habit in due if habit.completed_today), len(due)
