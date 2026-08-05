from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from tasks.models import Task


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
    completed_at = models.DateTimeField(null=True, blank=True)
    actual_focus_seconds = models.IntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.duration_minutes}min ({self.status})"