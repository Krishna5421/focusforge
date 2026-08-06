from django.db import models
from django.contrib.auth.models import User


class Achievement(models.Model):
    CRITERIA_CHOICES = [
        ('STREAK', 'Habit Streak'),
        ('TASKS_COMPLETED', 'Tasks Completed'),
        ('FOCUS_HOURS', 'Focus Hours'),
        ('STUDY_SESSIONS', 'Study Sessions'),
        ('GOALS_COMPLETED', 'Goals Completed'),
    ]

    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10)
    criteria_type = models.CharField(max_length=20, choices=CRITERIA_CHOICES)
    criteria_value = models.IntegerField()
    xp_reward = models.IntegerField(default=20)

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='unlocked_by')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"