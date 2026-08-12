from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from tasks.models import Task
from habits.models import Habit, HabitLog
from goals.models import Goal
from pomodoro.models import PomodoroSession
from achievements.models import UserAchievement


def percent_change(current, previous):
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100)


@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()
    week_start = today - timedelta(days=6)
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)

    todays_tasks_qs = Task.objects.filter(user=user, due_date__date=today)
    todays_tasks_count = todays_tasks_qs.count()
    completed_today_count = todays_tasks_qs.filter(status='COMPLETED').count()
    todays_tasks = todays_tasks_qs

    habits_qs = Habit.objects.filter(user=user, is_active=True)
    todays_habits = []
    for habit in habits_qs:
        completed_today = habit.logs.filter(date=today, completed=True).exists()
        todays_habits.append({'habit': habit, 'completed_today': completed_today})

    active_goals = Goal.objects.filter(user=user, status='ACTIVE')

    today_focus_seconds = 0
    todays_pomodoros = PomodoroSession.objects.filter(user=user, started_at__date=today, status='COMPLETED')
    for session in todays_pomodoros:
        today_focus_seconds += session.actual_focus_seconds
    today_focus_minutes = today_focus_seconds // 60
    pomodoro_sessions_today = todays_pomodoros.count()

    deadline_items = []
    upcoming_tasks = Task.objects.filter(
        user=user, status__in=['PENDING', 'IN_PROGRESS'], due_date__isnull=False, due_date__date__gte=today
    ).order_by('due_date')[:5]
    for task in upcoming_tasks:
        deadline_items.append({'title': task.title, 'date': task.due_date})

    upcoming_goals = Goal.objects.filter(user=user, status='ACTIVE', deadline__gte=today).order_by('deadline')[:5]
    for goal in upcoming_goals:
        deadline_items.append({'title': goal.title, 'date': goal.deadline})

    deadline_items.sort(key=lambda item: str(item['date']))
    deadlines_preview = deadline_items[:3]

    week_tasks_completed = Task.objects.filter(
        user=user, status='COMPLETED', completed_at__date__gte=week_start, completed_at__date__lte=today
    ).count()

    week_focus_seconds = 0
    for session in PomodoroSession.objects.filter(
        user=user, started_at__date__gte=week_start, started_at__date__lte=today, status='COMPLETED'
    ):
        week_focus_seconds += session.actual_focus_seconds
    week_focus_minutes = week_focus_seconds // 60

    week_habits_completed = HabitLog.objects.filter(
        habit__user=user, date__gte=week_start, date__lte=today, completed=True
    ).count()

    prev_week_tasks_completed = Task.objects.filter(
        user=user, status='COMPLETED', completed_at__date__gte=prev_week_start, completed_at__date__lte=prev_week_end
    ).count()

    prev_week_focus_seconds = 0
    for session in PomodoroSession.objects.filter(
        user=user, started_at__date__gte=prev_week_start, started_at__date__lte=prev_week_end, status='COMPLETED'
    ):
        prev_week_focus_seconds += session.actual_focus_seconds
    prev_week_focus_minutes = prev_week_focus_seconds // 60

    prev_week_habits_completed = HabitLog.objects.filter(
        habit__user=user, date__gte=prev_week_start, date__lte=prev_week_end, completed=True
    ).count()

    tasks_delta = percent_change(week_tasks_completed, prev_week_tasks_completed)
    focus_delta = percent_change(week_focus_minutes, prev_week_focus_minutes)
    habits_delta = percent_change(week_habits_completed, prev_week_habits_completed)

    profile = user.profile
    recent_achievements = UserAchievement.objects.filter(user=user)[:4]

    context = {
        'todays_tasks': todays_tasks,
        'todays_tasks_count': todays_tasks_count,
        'completed_today_count': completed_today_count,
        'todays_habits': todays_habits,
        'active_goals': active_goals,
        'active_goals_count': active_goals.count(),
        'today_focus_minutes': today_focus_minutes,
        'pomodoro_sessions_today': pomodoro_sessions_today,
        'deadlines_preview': deadlines_preview,
        'week_tasks_completed': week_tasks_completed,
        'week_focus_minutes': week_focus_minutes,
        'week_habits_completed': week_habits_completed,
        'tasks_delta': tasks_delta,
        'focus_delta': focus_delta,
        'habits_delta': habits_delta,
        'profile': profile,
        'recent_achievements': recent_achievements,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def deadlines(request):
    user = request.user
    today = timezone.now().date()
    later_limit = today + timedelta(days=14)

    items = []

    tasks = Task.objects.filter(
        user=user,
        status__in=['PENDING', 'IN_PROGRESS'],
        due_date__date__lte=later_limit,
        due_date__isnull=False
    )
    for task in tasks:
        items.append({
            'type': 'Task',
            'title': task.title,
            'date': task.due_date.date(),
        })

    goals = Goal.objects.filter(user=user, status='ACTIVE', deadline__lte=later_limit)
    for goal in goals:
        items.append({
            'type': 'Goal',
            'title': goal.title,
            'date': goal.deadline,
        })

    items.sort(key=lambda item: item['date'])

    grouped = {'Today': [], 'Tomorrow': [], 'This Week': [], 'Later': []}
    tomorrow = today + timedelta(days=1)
    week_limit = today + timedelta(days=7)

    for item in items:
        if item['date'] == today:
            grouped['Today'].append(item)
        elif item['date'] == tomorrow:
            grouped['Tomorrow'].append(item)
        elif item['date'] <= week_limit:
            grouped['This Week'].append(item)
        else:
            grouped['Later'].append(item)

    return render(request, 'core/deadlines.html', {'grouped': grouped})


@login_required
def analytics_page(request):
    return render(request, 'core/analytics.html')