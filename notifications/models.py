from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    TYPE_CHOICES = [
        ('TASK_REMINDER', 'Task Reminder'),
        ('HABIT_REMINDER', 'Habit Reminder'),
        ('GOAL_DEADLINE', 'Goal Deadline'),
        ('POMODORO_ABANDONED', 'Pomodoro Abandoned'),
        ('FOCUS_COMPLETED', 'Focus Session Completed'),
        ('TASK_COMPLETED', 'Task Completed'),
        ('HABIT_COMPLETED', 'Habit Completed'),
        ('STREAK_MILESTONE', 'Streak Milestone'),
        ('STUDY_COMPLETED', 'Study Session Completed'),
        ('MILESTONE_COMPLETED', 'Milestone Completed'),
        ('GOAL_COMPLETED', 'Goal Completed'),
        ('ACHIEVEMENT_UNLOCKED', 'Achievement Unlocked'),
        ('STUDY_REMINDER', 'Study Reminder'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_object_id = models.IntegerField(null=True, blank=True)

    is_read = models.BooleanField(default=False)
    sent_via_email = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"
