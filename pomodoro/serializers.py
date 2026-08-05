from rest_framework import serializers
from .models import PomodoroSession


class PomodoroSessionSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)

    class Meta:
        model = PomodoroSession
        fields = [
            'id', 'task', 'task_title', 'duration_minutes', 'status',
            'started_at', 'completed_at', 'actual_focus_seconds'
        ]
        read_only_fields = ['started_at', 'completed_at']