from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db import models
from datetime import timedelta

from tasks.models import Task
from habits.models import Habit
from goals.models import Goal
from study.models import StudySession
from pomodoro.models import PomodoroSession
from .models import AIQueryLog
from .utils import MAX_QUERIES

@login_required
def assistant_page(request):
    user = request.user
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    # --- Productivity Summary Data ---
    
    # Tasks (Fallback to overall if none due specifically today to keep UI populated)
    tasks_due_today = Task.objects.filter(user=user, due_date__date=today)
    if tasks_due_today.exists():
        tasks_total = tasks_due_today.count()
        tasks_completed = tasks_due_today.filter(status='COMPLETED').count()
    else:
        tasks_total = Task.objects.filter(user=user, status__in=['PENDING', 'IN_PROGRESS', 'COMPLETED']).count()
        tasks_completed = Task.objects.filter(user=user, status='COMPLETED').count()

    # Focus Time
    study_focus = StudySession.objects.filter(user=user, date=today).aggregate(total=models.Sum('duration_minutes'))['total'] or 0
    pomodoro_seconds = PomodoroSession.objects.filter(user=user, started_at__date=today, status='COMPLETED').aggregate(total=models.Sum('actual_focus_seconds'))['total'] or 0
    focus_mins_today = study_focus + pomodoro_seconds // 60
    focus_hours = focus_mins_today // 60
    focus_mins = focus_mins_today % 60

    # Habits
    active_habits = Habit.objects.filter(user=user, is_active=True)
    habits_total = active_habits.count()
    habits_completed = sum(1 for h in active_habits if h.logs.filter(date=today, completed=True).exists())

    # Goals Average Progress
    active_goals = Goal.objects.filter(user=user, status='ACTIVE')
    goals_avg_progress = active_goals.aggregate(avg=models.Avg('completion_percentage'))['avg'] or 0
    goals_avg_progress = int(round(goals_avg_progress))

    # --- Recent Activity Feed ---
    recent_activity = []
    
    # Get recently completed tasks
    for t in Task.objects.filter(user=user, status='COMPLETED').order_by('-updated_at')[:2]:
        recent_activity.append({'icon': '✓', 'text': f'Completed "{t.title}"', 'type': 'success'})

    # Get recently completed habits today
    for h in Habit.objects.filter(user=user, logs__date=today, logs__completed=True).distinct()[:2]:
        recent_activity.append({'icon': '✓', 'text': f'Completed {h.name}', 'type': 'success'})

    # Get recent focus sessions
    for s in StudySession.objects.filter(user=user).order_by('-date', '-id')[:1]:
        recent_activity.append({'icon': '◷', 'text': f'{s.duration_minutes} min focus session', 'type': 'info'})

    recent_activity = recent_activity[:4] # Limit to 4 items

    context = {
        'tasks_completed': tasks_completed,
        'tasks_total': tasks_total,
        'focus_hours': focus_hours,
        'focus_mins': focus_mins,
        'habits_completed': habits_completed,
        'habits_total': habits_total,
        'goals_avg_progress': goals_avg_progress,
        'recent_activity': recent_activity,
        'chat_history': AIQueryLog.objects.filter(user=user, created_at__date=today).order_by('created_at', 'pk'),
        'messages_today': AIQueryLog.objects.filter(user=user, created_at__date=today).count(),
        'message_limit': MAX_QUERIES,
    }

    return render(request, 'assistant/assistant.html', context)
