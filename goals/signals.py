from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Goal, Milestone
from achievements.utils import award_xp, check_goal_achievements, check_milestone_achievements


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


@receiver(pre_save, sender=Goal)
def remember_previous_goal_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_achievement_status = (
            Goal.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        )
    else:
        instance._previous_achievement_status = None


@receiver(post_save, sender=Goal)
def check_completed_goal_achievements(sender, instance, created, **kwargs):
    previous_status = getattr(instance, '_previous_achievement_status', None)
    if instance.status == 'COMPLETED' and (created or previous_status != 'COMPLETED'):
        check_goal_achievements(instance.user)


@receiver(post_save, sender=Milestone)
def update_goal_on_milestone_save(sender, instance, **kwargs):
    if instance.is_completed and not instance.completed_at:
        instance.completed_at = timezone.now()
        Milestone.objects.filter(pk=instance.pk).update(completed_at=instance.completed_at)
        award_xp(instance.goal.user, 'MILESTONE_COMPLETED')
    recalculate_goal_progress(instance.goal)

    if instance.is_completed:
        check_milestone_achievements(instance.goal.user)

    if instance.goal.status == 'COMPLETED':
        award_xp(instance.goal.user, 'GOAL_COMPLETED')


@receiver(post_delete, sender=Milestone)
def update_goal_on_milestone_delete(sender, instance, origin=None, **kwargs):
    # Skip when the whole account is being deleted; the goal is going away too.
    if isinstance(origin, User):
        return
    recalculate_goal_progress(instance.goal)
