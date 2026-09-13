from .models import Notification


def notify_once(user, notification_type, title, message, related_object_id=None):
    """Create one durable in-app notification for a specific user event."""
    filters = {
        'user': user,
        'type': notification_type,
        'related_object_id': related_object_id,
    }
    notification, _ = Notification.objects.get_or_create(defaults={
        'title': title,
        'message': message,
    }, **filters)
    return notification
