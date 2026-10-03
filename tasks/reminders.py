"""Due-soon and overdue task notifications, checked while the user is on the site.

Render's free tier sleeps between requests, so instead of a background scheduler
the browser polls and each poll runs these checks for the signed-in user.
"""
import logging
from datetime import timedelta

from django.db.models import F
from django.utils import dateformat, timezone

from notifications.models import Notification
from .models import Task

logger = logging.getLogger(__name__)

DUE_SOON_WINDOW = timedelta(hours=1)
# Tasks that went overdue long ago are not announced, so a returning user is not flooded.
OVERDUE_LOOKBACK = timedelta(days=7)
OPEN_STATUSES = ['PENDING', 'IN_PROGRESS']


def format_due(due_date):
    local_due = timezone.localtime(due_date)
    if local_due.date() == timezone.localdate():
        return f"today at {dateformat.format(local_due, 'g:i A')}"
    return dateformat.format(local_due, 'M j \\a\\t g:i A')


def claim_reminder(task, field):
    """Mark the reminder as sent for this due date; False if another request already did."""
    return Task.objects.filter(pk=task.pk, due_date=task.due_date).exclude(
        **{field: task.due_date}
    ).update(**{field: task.due_date}) == 1


def notify_task(task, notification_type, title, message):
    Notification.objects.create(
        user=task.user,
        type=notification_type,
        title=title,
        message=message,
        related_object_id=task.pk,
        toast_pending=True,
    )


def check_task_due_notifications(user, now=None):
    """Create due-soon and overdue notifications for the user's open tasks. Returns how many were created."""
    now = now or timezone.now()
    open_tasks = Task.objects.filter(user=user, status__in=OPEN_STATUSES, due_date__isnull=False)
    created = 0

    due_soon = open_tasks.filter(
        due_date__gt=now, due_date__lte=now + DUE_SOON_WINDOW,
    ).exclude(due_soon_notified_for=F('due_date'))
    for task in due_soon:
        if claim_reminder(task, 'due_soon_notified_for'):
            notify_task(task, 'TASK_DUE_SOON', 'Task due soon',
                        f'“{task.title}” is due {format_due(task.due_date)}.')
            created += 1

    overdue = open_tasks.filter(
        due_date__lte=now, due_date__gte=now - OVERDUE_LOOKBACK,
    ).exclude(overdue_notified_for=F('due_date'))
    for task in overdue:
        if claim_reminder(task, 'overdue_notified_for'):
            notify_task(task, 'TASK_OVERDUE', 'Task overdue',
                        f'“{task.title}” was due {format_due(task.due_date)}.')
            created += 1

    return created


def safe_check_task_due_notifications(user):
    """Run the reminder check without ever breaking the request that triggered it."""
    try:
        return check_task_due_notifications(user)
    except Exception:
        logger.exception('Task due reminder check failed for user %s', user.pk)
        return 0
