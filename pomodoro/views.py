from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from .models import PomodoroSession


@login_required
def pomodoro_page(request):
    recent_sessions = PomodoroSession.objects.filter(user=request.user)[:10]
    return render(request, 'pomodoro/pomodoro.html', {'recent_sessions': recent_sessions})


@login_required
def pomodoro_start(request):
    task_id = request.POST.get('task_id')
    duration = request.POST.get('duration', 25)

    session = PomodoroSession.objects.create(
        user=request.user,
        task_id=task_id if task_id else None,
        duration_minutes=duration,
        status='RUNNING',
    )
    return JsonResponse({'session_id': session.id, 'status': session.status})


@login_required
def pomodoro_update(request, pk):
    session = get_object_or_404(PomodoroSession, pk=pk, user=request.user)
    new_status = request.POST.get('status')
    focus_seconds = request.POST.get('focus_seconds', 0)

    session.status = new_status
    session.actual_focus_seconds = focus_seconds

    if new_status == 'COMPLETED':
        session.completed_at = timezone.now()

    session.save()
    return JsonResponse({'status': session.status})