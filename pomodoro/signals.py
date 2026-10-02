from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from achievements.utils import check_focus_achievements
from .models import PomodoroSession


@receiver(pre_save, sender=PomodoroSession)
def remember_previous_focus_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_achievement_status = (
            PomodoroSession.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        )
    else:
        instance._previous_achievement_status = None


@receiver(post_save, sender=PomodoroSession)
def check_completed_focus_achievements(sender, instance, created, **kwargs):
    previous_status = getattr(instance, '_previous_achievement_status', None)
    if instance.status == 'COMPLETED' and (created or previous_status != 'COMPLETED'):
        check_focus_achievements(instance.user)
