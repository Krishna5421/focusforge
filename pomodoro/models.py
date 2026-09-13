from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from tasks.models import Task


class PomodoroSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pomodoro_settings')
    daily_goal = models.PositiveSmallIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )

    def __str__(self):
        return f"{self.user.username}'s Pomodoro settings"


class PomodoroSession(models.Model):
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
        ('STOPPED', 'Stopped'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pomodoro_sessions')
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='pomodoro_sessions')

    duration_minutes = models.IntegerField(
        default=25,
        validators=[MinValueValidator(5), MaxValueValidator(120)]
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='RUNNING')

    started_at = models.DateTimeField(auto_now_add=True)
    last_resumed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    actual_focus_seconds = models.IntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.duration_minutes}min ({self.status})"
