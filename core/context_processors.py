from tasks.models import Task
from notifications.models import Notification


def sidebar_data(request):
    if not request.user.is_authenticated:
        return {}

    return {
        'sidebar_open_tasks': Task.objects.filter(
            user=request.user,
            status__in=['PENDING', 'IN_PROGRESS'],
        ).count(),
        'sidebar_unread_notifications': Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count(),
    }
