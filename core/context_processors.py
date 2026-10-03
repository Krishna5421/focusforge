from datetime import timedelta

from django.utils import timezone

from goals.models import Goal
from tasks.models import Task
from notifications.models import Notification

# Same window as the Deadlines page, so its badge matches what the page lists.
DEADLINE_WINDOW_DAYS = 14


def sidebar_data(request):
    if not request.user.is_authenticated:
        return {}

    from habits.schedule import annotate_habits

    user = request.user
    today = timezone.localdate()
    deadline_limit = today + timedelta(days=DEADLINE_WINDOW_DAYS)
    _, habits_done, habits_due = annotate_habits(user, today)

    return {
        'sidebar_open_tasks': Task.objects.filter(
            user=user,
            status__in=['PENDING', 'IN_PROGRESS'],
        ).count(),
        'sidebar_habits_left': habits_due - habits_done,
        'sidebar_active_goals': Goal.objects.filter(user=user, status='ACTIVE').count(),
        'sidebar_deadlines': (
            Task.objects.filter(user=user, status__in=['PENDING', 'IN_PROGRESS'],
                                due_date__isnull=False, due_date__date__lte=deadline_limit).count()
            + Goal.objects.filter(user=user, status='ACTIVE', deadline__lte=deadline_limit).count()
        ),
        'sidebar_unread_notifications': Notification.objects.filter(
            user=user,
            is_read=False,
        ).count(),
    }
