from django.db.models.signals import post_save
from django.dispatch import receiver

from achievements.utils import check_study_achievements
from .models import StudySession


@receiver(post_save, sender=StudySession)
def check_study_session_achievements(sender, instance, created, **kwargs):
    if created:
        check_study_achievements(instance.user)
