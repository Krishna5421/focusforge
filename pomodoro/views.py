from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from tasks.models import Task
from study.models import ActiveStudySession
from .models import PomodoroSession, PomodoroSettings


@login_required
def pomodoro_page(request):
    recent_sessions = list(PomodoroSession.objects.filter(user=request.user).select_related('task')[:30])
    today = timezone.localdate()
    sessions = PomodoroSession.objects.filter(user=request.user, status__in=['COMPLETED', 'STOPPED'], actual_focus_seconds__gt=0)
    completed_today = sessions.filter(started_at__date=today).count()
    completed_yesterday = sessions.filter(started_at__date=today - timedelta(days=1)).count()
    today_focus_seconds = sum(
        session.actual_focus_seconds
        for session in sessions.filter(started_at__date=today)
    )

    for session in recent_sessions:
        seconds = session.actual_focus_seconds or session.duration_minutes * 60
        session.display_minutes = max(1, round(seconds / 60))

    streak = 0
    streak_day = today
    while sessions.filter(started_at__date=streak_day).exists():
        streak += 1
        streak_day -= timedelta(days=1)

    goal, _ = PomodoroSettings.objects.get_or_create(user=request.user)
    daily_goal = goal.daily_goal
    focus_score = min(100, completed_today * 20)
    tasks = Task.objects.filter(user=request.user).exclude(status='COMPLETED')
    active_pomodoro = PomodoroSession.objects.filter(
        user=request.user, status__in=['RUNNING', 'PAUSED'],
    ).select_related('task').order_by('-started_at').first()
    active_focus_remaining = 25 * 60
    if active_pomodoro:
        active_elapsed = active_pomodoro.actual_focus_seconds
        if active_pomodoro.status == 'RUNNING':
            active_elapsed += max(0, int((timezone.now() - (active_pomodoro.last_resumed_at or active_pomodoro.started_at)).total_seconds()))
        active_focus_remaining = max(0, active_pomodoro.duration_minutes * 60 - active_elapsed)
    return render(request, 'pomodoro/pomodoro.html', {
        'recent_sessions': recent_sessions,
        'tasks': tasks,
        'completed_today': completed_today,
        'today_focus_minutes': today_focus_seconds // 60,
        'daily_goal': daily_goal,
        'goal_numbers': range(1, 21),
        'goal_percent': min(100, round((completed_today / daily_goal) * 100)),
        'focus_score': focus_score,
        'score_change': focus_score - min(100, completed_yesterday * 20),
        'streak': streak,
        'active_pomodoro': active_pomodoro,
        'active_focus_remaining': active_focus_remaining,
    })


@login_required
def update_daily_goal(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    try:
        daily_goal = int(request.POST.get('daily_goal', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Enter a whole number from 1 to 20.'}, status=400)

    if not 1 <= daily_goal <= 20:
        return JsonResponse({'error': 'Daily goal must be between 1 and 20.'}, status=400)

    goal, _ = PomodoroSettings.objects.get_or_create(user=request.user)
    goal.daily_goal = daily_goal
    goal.save(update_fields=['daily_goal'])
    return JsonResponse({'daily_goal': goal.daily_goal})


@login_required
def pomodoro_start(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    task_id = request.POST.get('task_id')
    try:
        duration = int(request.POST.get('duration', 25))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Enter a valid session duration.'}, status=400)
    if not 5 <= duration <= 120:
        return JsonResponse({'error': 'Session duration must be between 5 and 120 minutes.'}, status=400)
    task = get_object_or_404(Task, pk=task_id, user=request.user) if task_id else None

    active = PomodoroSession.objects.filter(user=request.user, status__in=['RUNNING', 'PAUSED']).order_by('-started_at').first()
    if active:
        elapsed = active.actual_focus_seconds
        if active.status == 'RUNNING':
            elapsed += max(0, int((timezone.now() - (active.last_resumed_at or active.started_at)).total_seconds()))
        return JsonResponse({
            'session_id': active.pk, 'status': active.status,
            'remaining_seconds': max(0, active.duration_minutes * 60 - elapsed),
            'duration_minutes': active.duration_minutes, 'existing': True,
        })
    if ActiveStudySession.objects.filter(user=request.user, has_started=True).exists():
        return JsonResponse({'error': 'Save or stop your active study session before starting a focus session.'}, status=409)

    session = PomodoroSession.objects.create(
        user=request.user,
        task=task,
        duration_minutes=duration,
        status='RUNNING',
        last_resumed_at=timezone.now(),
    )
    return JsonResponse({'session_id': session.id, 'status': session.status})


@login_required
def pomodoro_update(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    session = get_object_or_404(PomodoroSession, pk=pk, user=request.user)
    was_completed = session.status == 'COMPLETED'
    new_status = request.POST.get('status')
    if new_status not in dict(PomodoroSession.STATUS_CHOICES):
        return JsonResponse({'error': 'Invalid session status.'}, status=400)
    try:
        focus_seconds = int(request.POST.get('focus_seconds', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Enter valid focus seconds.'}, status=400)
    if focus_seconds < 0 or focus_seconds > session.duration_minutes * 60:
        return JsonResponse({'error': 'Focus seconds are outside this session duration.'}, status=400)

    session.status = new_status
    session.actual_focus_seconds = focus_seconds
    session.last_resumed_at = timezone.now() if new_status == 'RUNNING' else None

    if new_status == 'COMPLETED':
        session.completed_at = timezone.now()

    session.save()
    if new_status == 'COMPLETED' and not was_completed:
        from notifications.utils import notify_once
        minutes = max(1, round(session.actual_focus_seconds / 60))
        notify_once(request.user, 'FOCUS_COMPLETED', 'Focus session completed',
                    f'{minutes} minutes of focused work completed.', session.pk)
    today = timezone.localdate()
    saved_sessions = PomodoroSession.objects.filter(
        user=request.user, started_at__date=today,
        status__in=['COMPLETED', 'STOPPED'], actual_focus_seconds__gt=0,
    )
    return JsonResponse({
        'status': session.status,
        'focus_seconds': session.actual_focus_seconds,
        'task': session.task.title if session.task else None,
        'display_minutes': max(1, round(session.actual_focus_seconds / 60)),
        'today_sessions': saved_sessions.count(),
        'today_focus_minutes': sum(item.actual_focus_seconds for item in saved_sessions) // 60,
    })
