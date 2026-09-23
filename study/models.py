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
    planned_minutes = models.IntegerField(default=0)
    actual_seconds = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    resource_name = models.CharField(max_length=255, blank=True)
    resource_file = models.FileField(upload_to='study_files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.subject.name} - {self.date} ({self.duration_minutes} min)"


class ActiveStudySession(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='active_study_session')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='active_sessions')
    planned_minutes = models.IntegerField()
    remaining_seconds = models.IntegerField()
    notes = models.TextField(blank=True)
    resource_name = models.CharField(max_length=255, blank=True)
    resource_file = models.FileField(upload_to='study_files/', blank=True, null=True)
    is_running = models.BooleanField(default=False)
    has_started = models.BooleanField(default=False)
    timer_started_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class StudyFileLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_file_logs')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='file_logs')
    file_name = models.CharField(max_length=255)
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.file_name} ({self.user.username})"
