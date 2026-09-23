from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from urllib.parse import urlencode

from tasks.models import Task
from habits.models import Habit, HabitLog
from goals.models import Goal
from pomodoro.models import PomodoroSession
from achievements.models import UserAchievement
from study.models import ActiveStudySession, StudySession


def percent_change(current, previous):
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100)


@login_required
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    hour = timezone.localtime().hour
    greeting = 'Good morning' if hour < 12 else 'Good afternoon' if hour < 18 else 'Good evening'
    week_start = today - timedelta(days=6)
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)

    todays_tasks_qs = Task.objects.filter(user=user, due_date__date=today)
    todays_tasks_count = todays_tasks_qs.count()
    completed_today_count = todays_tasks_qs.filter(status='COMPLETED').count()
    todays_tasks = todays_tasks_qs

    habits_qs = Habit.objects.filter(user=user, is_active=True)
    habit_week_dates = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    todays_habits = []
    for habit in habits_qs:
        completed_today = habit.logs.filter(date=today, completed=True).exists()
        completed_dates = set(habit.logs.filter(date__range=(habit_week_dates[0], today), completed=True).values_list('date', flat=True))
        todays_habits.append({
            'habit': habit,
            'completed_today': completed_today,
            'week': [{'date': day, 'completed': day in completed_dates, 'is_today': day == today} for day in habit_week_dates],
        })
    completed_habits_count = sum(1 for item in todays_habits if item['completed_today'])

    active_goals = Goal.objects.filter(user=user, status='ACTIVE')
    goal_items = []
    for goal in active_goals:
        days_left = (goal.deadline - today).days
        goal_items.append({'goal': goal, 'days_left': days_left, 'overdue_days': max(0, -days_left)})

    today_focus_seconds = 0
    todays_pomodoros = PomodoroSession.objects.filter(
        user=user, started_at__date=today, status__in=['COMPLETED', 'STOPPED'], actual_focus_seconds__gt=0,
    )
    for session in todays_pomodoros:
        today_focus_seconds += session.actual_focus_seconds
    today_focus_minutes = today_focus_seconds // 60
    pomodoro_sessions_today = todays_pomodoros.count()

    deadline_items = []
    deadline_tasks = Task.objects.filter(
        user=user, status__in=['PENDING', 'IN_PROGRESS'], due_date__isnull=False
    )
    for task in deadline_tasks:
        date = task.due_date.date()
        deadline_items.append({'title': task.title, 'date': task.due_date, 'type': 'Task', 'days': (date - today).days})
    for goal in Goal.objects.filter(user=user, status='ACTIVE'):
        deadline_items.append({'title': goal.title, 'date': goal.deadline, 'type': 'Goal', 'days': (goal.deadline - today).days})
    # Overdue items first, then today's, then the nearest upcoming dates.
    deadline_items.sort(key=lambda item: (0 if item['days'] < 0 else 1, item['days'], str(item['date'])))
    deadlines_preview = deadline_items[:5]

    week_tasks_completed = Task.objects.filter(
        user=user, status='COMPLETED', completed_at__date__gte=week_start, completed_at__date__lte=today
    ).count()

    week_focus_seconds = 0
    for session in PomodoroSession.objects.filter(
        user=user, started_at__date__gte=week_start, started_at__date__lte=today,
        status__in=['COMPLETED', 'STOPPED'], actual_focus_seconds__gt=0,
    ):
        week_focus_seconds += session.actual_focus_seconds
    week_focus_minutes = week_focus_seconds // 60

    week_habits_completed = HabitLog.objects.filter(
        habit__user=user, date__gte=week_start, date__lte=today, completed=True
    ).count()

    week_dates = [week_start + timedelta(days=offset) for offset in range(7)]
    week_task_series = []
    week_focus_series = []
    week_habit_series = []
    for day in week_dates:
        week_task_series.append(Task.objects.filter(
            user=user, status='COMPLETED', completed_at__date=day
        ).count())
        focus_seconds = sum(session.actual_focus_seconds for session in PomodoroSession.objects.filter(
            user=user, status__in=['COMPLETED', 'STOPPED'], actual_focus_seconds__gt=0, started_at__date=day
        ))
        week_focus_series.append(round(focus_seconds / 60, 1))
        week_habit_series.append(HabitLog.objects.filter(
            habit__user=user, completed=True, date=day
        ).count())

    prev_week_tasks_completed = Task.objects.filter(
        user=user, status='COMPLETED', completed_at__date__gte=prev_week_start, completed_at__date__lte=prev_week_end
    ).count()

    prev_week_focus_seconds = 0
    for session in PomodoroSession.objects.filter(
        user=user, started_at__date__gte=prev_week_start, started_at__date__lte=prev_week_end,
        status__in=['COMPLETED', 'STOPPED'], actual_focus_seconds__gt=0,
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
    recent_study_sessions = StudySession.objects.filter(user=user).select_related('subject')[:4]

    context = {
        'todays_tasks': todays_tasks,
        'greeting': greeting,
        'todays_tasks_count': todays_tasks_count,
        'completed_today_count': completed_today_count,
        'todays_habits': todays_habits,
        'completed_habits_count': completed_habits_count,
        'active_goals': active_goals,
        'goal_items': goal_items,
        'active_goals_count': active_goals.count(),
        'today_focus_minutes': today_focus_minutes,
        'pomodoro_sessions_today': pomodoro_sessions_today,
        'deadlines_preview': deadlines_preview,
        'week_tasks_completed': week_tasks_completed,
        'week_focus_minutes': week_focus_minutes,
        'week_habits_completed': week_habits_completed,
        'productivity_chart': {
            'labels': [day.strftime('%a') for day in week_dates],
            'tasks': week_task_series,
            'focus': week_focus_series,
            'habits': week_habit_series,
        },
        'productivity_has_data': any(week_task_series) or any(week_focus_series) or any(week_habit_series),
        'tasks_delta': tasks_delta,
        'focus_delta': focus_delta,
        'habits_delta': habits_delta,
        'profile': profile,
        'xp_to_next_level': 100 - (profile.total_xp % 100) if profile.total_xp % 100 else 100,
        'xp_level_progress': profile.total_xp % 100,
        'recent_achievements': recent_achievements,
        'recent_study_sessions': recent_study_sessions,
    }

    active_pomodoro = PomodoroSession.objects.filter(
        user=user, status__in=['RUNNING', 'PAUSED'],
    ).select_related('task').order_by('-started_at').first()
    context['active_pomodoro'] = active_pomodoro
    context['active_focus_remaining'] = pomodoro_remaining_seconds(active_pomodoro) if active_pomodoro else 25 * 60
    return render(request, 'core/dashboard.html', context)


def pomodoro_remaining_seconds(session, now=None):
    now = now or timezone.now()
    elapsed = session.actual_focus_seconds
    if session.status == 'RUNNING':
        resumed_at = session.last_resumed_at or session.started_at
        elapsed += max(0, int((now - resumed_at).total_seconds()))
    return max(0, session.duration_minutes * 60 - elapsed)


@login_required
def active_timer_state(request):
    """Return this user's single active focus or study timer for the shared widget."""
    now = timezone.now()
    pomodoro = PomodoroSession.objects.filter(
        user=request.user, status__in=['RUNNING', 'PAUSED'],
    ).select_related('task').order_by('-started_at').first()
    study = ActiveStudySession.objects.filter(
        user=request.user, has_started=True,
    ).select_related('subject').first()

    if pomodoro and (not study or pomodoro.started_at >= study.updated_at):
        elapsed = pomodoro.duration_minutes * 60 - pomodoro_remaining_seconds(pomodoro, now)
        return JsonResponse({
            'active': True, 'source': 'focus', 'label': 'FOCUS',
            'title': pomodoro.task.title if pomodoro.task else '',
            'id': pomodoro.pk, 'running': pomodoro.status == 'RUNNING',
            'remaining_seconds': pomodoro_remaining_seconds(pomodoro, now),
            'elapsed_seconds': max(0, elapsed), 'duration_seconds': pomodoro.duration_minutes * 60,
            'update_url': reverse('pomodoro:pomodoro_update', args=[pomodoro.pk]),
        })
    if study:
        remaining = study.remaining_seconds
        if study.is_running and study.timer_started_at:
            remaining = max(0, remaining - int((now - study.timer_started_at).total_seconds()))
        duration = study.planned_minutes * 60
        return JsonResponse({
            'active': True, 'source': 'study', 'label': 'STUDY SESSION',
            'title': study.subject.name, 'id': study.pk, 'running': study.is_running,
            'remaining_seconds': remaining, 'elapsed_seconds': max(0, duration - remaining),
            'duration_seconds': duration,
            'start_url': reverse('study:active_session_timer', args=['start']),
            'pause_url': reverse('study:active_session_timer', args=['pause']),
            'save_url': reverse('study:active_session_save'),
        })
    return JsonResponse({'active': False})


@login_required
def global_search(request):
    query = (request.GET.get('q') or request.GET.get('search') or '').strip()
    if not query:
        messages.info(request, 'Enter a task, habit, or goal to search.')
        return redirect('core:dashboard')

    destinations = (
        ('tasks:task_list', Task.objects.filter(user=request.user, title__icontains=query)),
        ('habits:habit_list', Habit.objects.filter(user=request.user, is_active=True, name__icontains=query)),
        ('goals:goal_list', Goal.objects.filter(user=request.user, title__icontains=query)),
    )
    for view_name, results in destinations:
        if results.exists():
            messages.success(request, f'Matching results found for “{query}”.')
            return redirect(f'{reverse(view_name)}?{urlencode({"search": query})}')

    messages.warning(request, f'No tasks, habits, or goals were found for “{query}”.')
    return redirect('core:dashboard')


@login_required
def deadlines(request):
    user = request.user
    today = timezone.now().date()
    later_limit = today + timedelta(days=14)
    tomorrow = today + timedelta(days=1)
    week_limit = today + timedelta(days=7)
    grouped = {'Overdue': [], 'Today': [], 'Tomorrow': [], 'This Week': [], 'Later': []}

    tasks = Task.objects.filter(
        user=user, status__in=['PENDING', 'IN_PROGRESS'], due_date__isnull=False,
        due_date__date__lte=later_limit,
    ).order_by('due_date')
    for task in tasks:
        item = {
            'type': 'Task', 'title': task.title, 'date': task.due_date, 'task_id': task.id,
            'priority': task.get_priority_display(), 'priority_code': task.priority.lower(),
            'category': task.category.name if task.category else 'Task', 'description': task.description,
        }
        if task.due_date.date() < today:
            grouped['Overdue'].append(item)
        elif task.due_date.date() == today:
            grouped['Today'].append(item)
        elif task.due_date.date() == tomorrow:
            grouped['Tomorrow'].append(item)
        elif task.due_date.date() <= week_limit:
            grouped['This Week'].append(item)
        else:
            grouped['Later'].append(item)

    goals = Goal.objects.filter(user=user, status='ACTIVE', deadline__lte=later_limit).order_by('deadline')
    for goal in goals:
        item = {
            'type': 'Goal', 'title': goal.title, 'date': goal.deadline, 'goal_id': goal.id,
            'category': 'Goal', 'description': goal.description,
        }
        if goal.deadline < today:
            grouped['Overdue'].append(item)
        elif goal.deadline == today:
            grouped['Today'].append(item)
        elif goal.deadline == tomorrow:
            grouped['Tomorrow'].append(item)
        elif goal.deadline <= week_limit:
            grouped['This Week'].append(item)
        else:
            grouped['Later'].append(item)

    for items in grouped.values():
        items.sort(key=lambda item: str(item['date']))

    week_tasks = Task.objects.filter(user=user, due_date__date__gte=today, due_date__date__lte=week_limit)
    week_task_count = week_tasks.count()
    completed_week_count = week_tasks.filter(status='COMPLETED').count()
    performance = round((completed_week_count / week_task_count) * 100) if week_task_count else 0
    pressing = (grouped['Overdue'] + grouped['Today'])[:4]

    return render(request, 'core/deadlines.html', {
        'grouped': grouped,
        'overdue_count': len(grouped['Overdue']),
        'today_count': len(grouped['Today']),
        'week_count': len(grouped['Tomorrow']) + len(grouped['This Week']),
        'today_items': grouped['Today'],
        'week_items': grouped['Tomorrow'] + grouped['This Week'],
        'pressing': pressing,
        'performance': performance,
        'completed_week_count': completed_week_count,
        'week_task_count': week_task_count,
    })


@login_required
def analytics_page(request):
    return render(request, 'core/analytics.html')


@login_required
def analytics_data(request):
    period = request.GET.get('period', 'week')
    days_by_period = {'week': 7, 'month': 30, 'quarter': 90}
    days = days_by_period.get(period, 7)
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    dates = [start + timedelta(days=offset) for offset in range(days)]
    labels = [f'{day.strftime("%b")} {day.day}' for day in dates]

    focus_actual = {day: 0 for day in dates}
    focus_planned = {day: 0 for day in dates}
    sessions = PomodoroSession.objects.filter(user=request.user, started_at__date__range=(start, today))
    for session in sessions:
        day = timezone.localtime(session.started_at).date()
        if day not in focus_actual:
            continue
        focus_planned[day] += session.duration_minutes
        if session.status in ['COMPLETED', 'STOPPED'] and session.actual_focus_seconds:
            focus_actual[day] += session.actual_focus_seconds / 60

    tasks_by_day = {day: 0 for day in dates}
    for task in Task.objects.filter(user=request.user, status='COMPLETED', completed_at__date__range=(start, today)):
        if task.completed_at:
            tasks_by_day[timezone.localtime(task.completed_at).date()] += 1

    active_habits = Habit.objects.filter(user=request.user, is_active=True)
    habit_done = {day: 0 for day in dates}
    for log in HabitLog.objects.filter(habit__user=request.user, completed=True, date__range=(start, today)):
        habit_done[log.date] += 1
    habit_percent = []
    for day in dates:
        applicable = sum(1 for habit in active_habits if habit.created_at.date() <= day)
        habit_percent.append(round((habit_done[day] / applicable) * 100, 1) if applicable else 0)

    study_by_subject = {}
    study_sessions = StudySession.objects.filter(user=request.user, date__range=(start, today)).select_related('subject')
    for session in study_sessions:
        actual_minutes = session.actual_seconds / 60 if session.actual_seconds else session.duration_minutes
        study_by_subject[session.subject.name] = study_by_subject.get(session.subject.name, 0) + actual_minutes

    goals = Goal.objects.filter(user=request.user).exclude(status='ABANDONED').order_by('-created_at')[:12]
    return JsonResponse({
        'period': period,
        'labels': labels,
        'focus': {'actual': [round(focus_actual[day], 1) for day in dates], 'planned': [round(focus_planned[day], 1) for day in dates]},
        'tasks': [tasks_by_day[day] for day in dates],
        'habits': habit_percent,
        'study': {'labels': list(study_by_subject.keys()), 'data': [round(value, 1) for value in study_by_subject.values()]},
        'goals': {'labels': [goal.title for goal in goals], 'data': [goal.completion_percentage for goal in goals]},
    })
