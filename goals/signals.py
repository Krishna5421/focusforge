from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Milestone


def recalculate_goal_progress(goal):
    milestones = goal.milestones.all()
    total = milestones.count()

    if total == 0:
        goal.completion_percentage = 0
    else:
        completed = milestones.filter(is_completed=True).count()
        goal.completion_percentage = int((completed / total) * 100)

        if goal.completion_percentage == 100 and goal.status == 'ACTIVE':
            goal.status = 'COMPLETED'

    goal.save(update_fields=['completion_percentage', 'status'])


@receiver(post_save, sender=Milestone)
def update_goal_on_milestone_save(sender, instance, **kwargs):
    if instance.is_completed and not instance.completed_at:
        instance.completed_at = timezone.now()
        Milestone.objects.filter(pk=instance.pk).update(completed_at=instance.completed_at)
    recalculate_goal_progress(instance.goal)


@receiver(post_delete, sender=Milestone)
def update_goal_on_milestone_delete(sender, instance, **kwargs):
    recalculate_goal_progress(instance.goal)