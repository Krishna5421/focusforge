from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from achievements.utils import award_xp, remove_xp
from .models import Task
from notifications.utils import notify_once


@receiver(pre_save, sender=Task)
def track_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Task.objects.get(pk=instance.pk).status
        except Task.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Task)
def update_task_completion(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)

    if instance.status == 'COMPLETED' and old_status != 'COMPLETED':
        if not instance.completed_at:
            instance.completed_at = timezone.now()
            Task.objects.filter(pk=instance.pk).update(completed_at=instance.completed_at)

        if not instance.xp_awarded:
            award_xp(instance.user, 'TASK_COMPLETED')
            Task.objects.filter(pk=instance.pk).update(xp_awarded=True)
        notify_once(instance.user, 'TASK_COMPLETED', 'Task completed', f'You completed “{instance.title}”.', instance.pk)

    if old_status == 'COMPLETED' and instance.status != 'COMPLETED' and instance.xp_awarded:
        remove_xp(instance.user, 'TASK_COMPLETED')
        Task.objects.filter(pk=instance.pk).update(xp_awarded=False)
