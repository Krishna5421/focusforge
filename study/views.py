from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Subject, StudySession, ActiveStudySession
from .forms import SubjectForm, StudySessionForm
from pomodoro.models import PomodoroSession


@login_required
def study_dashboard(request):
    subjects = Subject.objects.filter(user=request.user).order_by('name')
    all_sessions = StudySession.objects.filter(user=request.user).select_related('subject')
    sessions = list(all_sessions[:30])
    for session in sessions:
        session.planned_display = session.planned_minutes or session.duration_minutes
        seconds = session.actual_seconds or session.duration_minutes * 60
        session.actual_display = f'{seconds // 60}m {seconds % 60}s' if seconds % 60 else f'{seconds // 60}m'
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    total_minutes = sum(session.duration_minutes for session in all_sessions)
    week_minutes = sum(session.duration_minutes for session in all_sessions.filter(date__gte=week_start))
    session_count = all_sessions.count()

    active_session = ActiveStudySession.objects.filter(user=request.user).select_related('subject').first()
    active_remaining = active_session.remaining_seconds if active_session else 0
    if active_session and active_session.is_running and active_session.timer_started_at:
        elapsed = int((timezone.now() - active_session.timer_started_at).total_seconds())
        active_remaining = max(0, active_session.remaining_seconds - elapsed)
    return render(request, 'study/study_dashboard.html', {
        'subjects': subjects,
        'sessions': sessions,
        'total_minutes': total_minutes,
        'week_minutes': week_minutes,
        'session_count': session_count,
        'average_minutes': round(total_minutes / session_count) if session_count else 0,
        'active_session': active_session,
        'active_remaining': active_remaining,
    })


@login_required
def subject_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method.'}, status=405)
    form = SubjectForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': form.errors.as_text()}, status=400)
    subject = form.save(commit=False)
    subject.user = request.user
    try:
        subject.save()
    except Exception:
        return JsonResponse({'error': 'You already have a subject with this name.'}, status=400)
    return JsonResponse({'id': subject.id, 'name': subject.name, 'color': subject.color})


@login_required
def study_session_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method.'}, status=405)
    subject_name = request.POST.get('subject_name', '').strip()
    if not subject_name:
        return JsonResponse({'error': 'Enter a subject name.'}, status=400)
    subject, _ = Subject.objects.get_or_create(user=request.user, name__iexact=subject_name, defaults={'name': subject_name})
    try:
        duration = int(request.POST.get('duration_minutes', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Enter a valid session length.'}, status=400)
    if not 1 <= duration <= 720:
        return JsonResponse({'error': 'Session length must be between 1 and 720 minutes.'}, status=400)
    session = StudySession.objects.create(
        user=request.user,
        subject=subject,
        date=timezone.localdate(),
        duration_minutes=duration,
        notes=request.POST.get('notes', '').strip(),
        resource_name=request.POST.get('resource_name', '').strip()[:255],
    )
    from notifications.utils import notify_once
    notify_once(request.user, 'STUDY_COMPLETED', 'Study session saved',
                f'{subject.name}: {duration} minutes logged.', session.pk)
    return JsonResponse({'id': session.id, 'subject': subject.name, 'duration': duration})


def active_remaining_seconds(active):
    if active.is_running and active.timer_started_at:
        elapsed = int((timezone.now() - active.timer_started_at).total_seconds())
        return max(0, active.remaining_seconds - elapsed)
    return active.remaining_seconds


@login_required
def active_session_setup(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method.'}, status=405)
    name = request.POST.get('subject_name', '').strip()
    if not name:
        return JsonResponse({'error': 'Enter a subject name.'}, status=400)
    if ActiveStudySession.objects.filter(user=request.user, has_started=True).exists():
        return JsonResponse({'error': 'Save or stop your active study session before setting up another one.'}, status=409)
    if PomodoroSession.objects.filter(user=request.user, status__in=['RUNNING', 'PAUSED']).exists():
        return JsonResponse({'error': 'Save or stop your active focus session before starting a study session.'}, status=409)
    subject, _ = Subject.objects.get_or_create(user=request.user, name__iexact=name, defaults={'name': name})
    try:
        minutes = int(request.POST.get('planned_minutes', 25))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Enter valid planned minutes.'}, status=400)
    if not 1 <= minutes <= 720:
        return JsonResponse({'error': 'Planned minutes must be between 1 and 720.'}, status=400)
    resource_name = request.POST.get('resource_name', '').strip()[:255]
    active, _ = ActiveStudySession.objects.update_or_create(
        user=request.user,
        defaults={'subject': subject, 'planned_minutes': minutes, 'remaining_seconds': minutes * 60,
                  'notes': request.POST.get('notes', '').strip(), 'resource_name': resource_name,
                  'resource_file': None,
                  'is_running': False, 'has_started': False, 'timer_started_at': None},
    )
    return JsonResponse({'id': active.id, 'remaining_seconds': active.remaining_seconds})


@login_required
def active_session_timer(request, action):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method.'}, status=405)
    active = get_object_or_404(ActiveStudySession, user=request.user)
    if request.POST.get('discard') == '1':
        active.delete()
        return JsonResponse({'discarded': True})
    if action == 'start' and PomodoroSession.objects.filter(user=request.user, status__in=['RUNNING', 'PAUSED']).exists():
        return JsonResponse({'error': 'Save or stop your active focus session before starting a study timer.'}, status=409)
    if action == 'start' and active.is_running:
        return JsonResponse({'remaining_seconds': active_remaining_seconds(active), 'is_running': True})
    if action == 'pause' and not active.is_running:
        return JsonResponse({'remaining_seconds': active.remaining_seconds, 'is_running': False})
    remaining = active_remaining_seconds(active)
    if action == 'start':
        active.remaining_seconds = remaining
        active.is_running = True
        active.has_started = True
        active.timer_started_at = timezone.now()
    elif action == 'pause':
        active.remaining_seconds = remaining
        active.is_running = False
        active.timer_started_at = None
    else:
        return JsonResponse({'error': 'Invalid timer action.'}, status=400)
    active.save()
    return JsonResponse({'remaining_seconds': active_remaining_seconds(active), 'is_running': active.is_running})


@login_required
def active_session_save(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method.'}, status=405)
    active = get_object_or_404(ActiveStudySession, user=request.user)
    remaining = active_remaining_seconds(active)
    actual_seconds = active.planned_minutes * 60 - remaining
    if actual_seconds < 1:
        return JsonResponse({'error': 'Start the timer before saving completed time.'}, status=400)
    duration = max(1, round(actual_seconds / 60))
    session = StudySession.objects.create(user=request.user, subject=active.subject, date=timezone.localdate(),
        duration_minutes=duration, planned_minutes=active.planned_minutes, actual_seconds=actual_seconds,
        notes=active.notes, resource_name=active.resource_name)
    from notifications.utils import notify_once
    notify_once(request.user, 'STUDY_COMPLETED', 'Study session saved',
                f'{session.subject.name}: {duration} minutes completed.', session.pk)
    active.delete()
    return JsonResponse({'duration_minutes': duration, 'actual_seconds': actual_seconds})
