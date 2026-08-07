from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from tasks.models import Task
from pomodoro.models import PomodoroSession
from goals.models import Goal
from .models import Notification


def check_pending_tasks():
    now = timezone.now()
    soon = now + timedelta(hours=24)

    pending_tasks = Task.objects.filter(
        status='PENDING',
        due_date__gte=now,
        due_date__lte=soon,
    )

    for task in pending_tasks:
        already_notified = Notification.objects.filter(
            user=task.user,
            type='TASK_REMINDER',
            related_object_id=task.id,
        ).exists()

        if not already_notified:
            Notification.objects.create(
                user=task.user,
                type='TASK_REMINDER',
                title='Task Due Soon',
                message=f'"{task.title}" is due within 24 hours.',
                related_object_id=task.id,
            )
            if task.user.email:
                send_mail(
                    subject='Task Due Soon ⏰',
                    message=f'Your task "{task.title}" is due within 24 hours. Don\'t forget to complete it!',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[task.user.email],
                    fail_silently=True,
                )


def check_abandoned_pomodoro_sessions():
    cutoff = timezone.now() - timedelta(hours=2)

    abandoned_sessions = PomodoroSession.objects.filter(
        status='RUNNING',
        started_at__lte=cutoff,
    )

    for session in abandoned_sessions:
        session.status = 'STOPPED'
        session.save()

        Notification.objects.create(
            user=session.user,
            type='POMODORO_ABANDONED',
            title='Pomodoro Session Left Running',
            message=f'Your {session.duration_minutes}-minute focus session was left running and has been auto-stopped.',
            related_object_id=session.id,
        )

        if session.user.email:
            send_mail(
                subject='Pomodoro Session Reminder 🍅',
                message='You started a focus session but never marked it complete. Stay consistent!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[session.user.email],
                fail_silently=True,
            )


def check_goal_deadlines():
    now = timezone.now().date()
    soon = now + timedelta(days=3)

    upcoming_goals = Goal.objects.filter(
        status='ACTIVE',
        deadline__gte=now,
        deadline__lte=soon,
    )

    for goal in upcoming_goals:
        already_notified = Notification.objects.filter(
            user=goal.user,
            type='GOAL_DEADLINE',
            related_object_id=goal.id,
        ).exists()

        if not already_notified:
            Notification.objects.create(
                user=goal.user,
                type='GOAL_DEADLINE',
                title='Goal Deadline Approaching',
                message=f'Your goal "{goal.title}" is due within 3 days.',
                related_object_id=goal.id,
            )
            if goal.user.email:
                send_mail(
                    subject='Goal Deadline Approaching 🎯',
                    message=f'Your goal "{goal.title}" is due within 3 days. Keep pushing!',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[goal.user.email],
                    fail_silently=True,
                )


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        check_pending_tasks,
        trigger='interval',
        hours=1,
        id='check_pending_tasks',
        replace_existing=True,
    )

    scheduler.add_job(
        check_abandoned_pomodoro_sessions,
        trigger='interval',
        minutes=30,
        id='check_abandoned_pomodoro',
        replace_existing=True,
    )

    scheduler.add_job(
        check_goal_deadlines,
        trigger='interval',
        hours=12,
        id='check_goal_deadlines',
        replace_existing=True,
    )

    scheduler.start()