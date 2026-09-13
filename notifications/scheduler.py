from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.contrib.auth import get_user_model
from django.utils import timezone

from tasks.models import Task
from pomodoro.models import PomodoroSession
from goals.models import Goal
from habits.models import Habit
from study.models import ActiveStudySession
from .models import Notification
from .emailing import send_focusforge_email_async
from .utils import notify_once


def check_pending_tasks():
    soon = timezone.now() + timedelta(hours=24)
    for task in Task.objects.filter(status__in=['PENDING', 'IN_PROGRESS'], due_date__range=(timezone.now(), soon)):
        if not Notification.objects.filter(user=task.user, type='TASK_REMINDER', related_object_id=task.id).exists():
            notify_once(task.user, 'TASK_REMINDER', 'Task due soon', f'“{task.title}” is due within 24 hours.', task.id)
            send_focusforge_email_async(task.user, 'FocusForge · Task due soon', 'A task is due soon',
                                        f'“{task.title}” is due within 24 hours. Plan a focused block to finish it.', '/tasks/')


def check_abandoned_pomodoro_sessions():
    cutoff = timezone.now() - timedelta(hours=2)
    for session in PomodoroSession.objects.filter(status='RUNNING', started_at__lte=cutoff):
        session.status = 'STOPPED'
        session.save(update_fields=['status'])
        notify_once(session.user, 'POMODORO_ABANDONED', 'Focus session left running',
                    f'Your {session.duration_minutes}-minute focus session was auto-stopped.', session.id)
        send_focusforge_email_async(session.user, 'FocusForge · Focus session paused', 'Your focus session was left running',
                                    'Your unfinished focus session was safely stopped. Resume when you are ready.', '/pomodoro/')


def check_goal_deadlines():
    today = timezone.localdate()
    for goal in Goal.objects.filter(status='ACTIVE', deadline__range=(today, today + timedelta(days=3))):
        if not Notification.objects.filter(user=goal.user, type='GOAL_DEADLINE', related_object_id=goal.id).exists():
            notify_once(goal.user, 'GOAL_DEADLINE', 'Goal deadline approaching', f'“{goal.title}” is due within 3 days.', goal.id)
            send_focusforge_email_async(goal.user, 'FocusForge · Goal deadline approaching', 'Your goal deadline is close',
                                        f'“{goal.title}” is due within 3 days. Review the remaining milestones today.', '/goals/')


def check_daily_incomplete_items():
    today = timezone.localdate()
    User = get_user_model()
    for user in User.objects.filter(is_active=True):
        if Notification.objects.filter(user=user, type='HABIT_REMINDER', created_at__date=today).exists():
            continue
        tasks = Task.objects.filter(user=user, status__in=['PENDING', 'IN_PROGRESS'], due_date__date=today).count()
        habits = Habit.objects.filter(user=user, is_active=True).exclude(logs__date=today, logs__completed=True).count()
        if tasks or habits:
            Notification.objects.create(user=user, type='HABIT_REMINDER', title='Today’s check-in',
                                        message=f'{tasks} task(s) and {habits} habit(s) still need attention.')
            send_focusforge_email_async(user, 'FocusForge · Today’s check-in', 'A quick end-of-day check-in',
                                        f'You have {tasks} task(s) and {habits} habit(s) still open for today.', '/')


def check_inactive_study_sessions():
    cutoff = timezone.now() - timedelta(hours=2)
    for session in ActiveStudySession.objects.select_related('subject').filter(updated_at__lte=cutoff):
        if not Notification.objects.filter(user=session.user, type='STUDY_REMINDER', related_object_id=session.pk).exists():
            notify_once(session.user, 'STUDY_REMINDER', 'Study session waiting',
                        f'Your {session.subject.name} study session is still unfinished.', session.pk)
            send_focusforge_email_async(session.user, 'FocusForge · Study session waiting', 'Your study session is still open',
                                        f'Your {session.subject.name} session has not been completed yet. Continue it when ready.', '/study/')


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), 'default')
    scheduler.add_job(check_pending_tasks, trigger='interval', hours=1, id='check_pending_tasks', replace_existing=True)
    scheduler.add_job(check_abandoned_pomodoro_sessions, trigger='interval', minutes=30, id='check_abandoned_pomodoro', replace_existing=True)
    scheduler.add_job(check_goal_deadlines, trigger='interval', hours=12, id='check_goal_deadlines', replace_existing=True)
    scheduler.add_job(check_daily_incomplete_items, trigger='cron', hour=19, minute=0, id='check_daily_incomplete_items', replace_existing=True)
    scheduler.add_job(check_inactive_study_sessions, trigger='interval', minutes=30, id='check_inactive_study_sessions', replace_existing=True)
    scheduler.start()
