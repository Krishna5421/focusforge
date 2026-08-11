from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from achievements.models import UserAchievement

from tasks.models import Task
from habits.models import Habit
from goals.models import Goal
from study.models import StudySession
from pomodoro.models import PomodoroSession


@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()

    todays_tasks_qs = Task.objects.filter(user=user, due_date__date=today)
    todays_tasks_count = todays_tasks_qs.count()
    completed_today_count = todays_tasks_qs.filter(status='COMPLETED').count()
    todays_tasks = todays_tasks_qs[:5]  # slice LAST, after all filtering/counting is done

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