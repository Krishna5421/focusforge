from django.db import models
from django.contrib.auth.models import User


class Habit(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, blank=True)  
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='DAILY')
    target_days = models.JSONField(default=list, blank=True)  # e.g. [1,2,3,4,5] for weekdays

    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def completion_rate(self):
        total_logs = self.logs.count()
        if total_logs == 0:
            return 0
        completed_logs = self.logs.filter(completed=True).count()
        return round((completed_logs / total_logs) * 100, 1)


class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField()
    completed = models.BooleanField(default=True)

    class Meta:
        unique_together = ('habit', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.habit.name} - {self.date}"