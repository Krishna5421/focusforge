from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Task
from achievements.utils import award_xp


@receiver(pre_save, sender=Task)
def track_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Task.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Task.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Task)
def send_completion_email(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)

    if instance.status == 'COMPLETED' and old_status != 'COMPLETED':
        if not instance.completed_at:
            instance.completed_at = timezone.now()
            Task.objects.filter(pk=instance.pk).update(completed_at=instance.completed_at)

        if instance.user.email:
            send_mail(
                subject='Task Completed 🎉',
                message=f'Great job completing "{instance.title}"! Keep up the momentum.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.user.email],
                fail_silently=True,
            )

        award_xp(instance.user, 'TASK_COMPLETED')