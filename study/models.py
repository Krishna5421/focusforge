from django.db import models
from django.contrib.auth.models import User


class Subject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#3b82f6')

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

    def total_hours(self):
        sessions = self.sessions.all()
        total_minutes = 0
        for s in sessions:
            total_minutes += s.duration_minutes
        return round(total_minutes / 60, 1)


class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='sessions')
    date = models.DateField()
    duration_minutes = models.IntegerField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.subject.name} - {self.date} ({self.duration_minutes} min)"


class StudyFileLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_file_logs')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='file_logs')
    file_name = models.CharField(max_length=255)
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.file_name} ({self.user.username})"