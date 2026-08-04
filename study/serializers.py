from rest_framework import serializers
from .models import Subject, StudySession, StudyFileLog


class SubjectSerializer(serializers.ModelSerializer):
    total_hours = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'name', 'color', 'total_hours']

    def get_total_hours(self, obj):
        return obj.total_hours()


class StudySessionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = StudySession
        fields = ['id', 'subject', 'subject_name', 'date', 'duration_minutes', 'notes', 'created_at']


class StudyFileLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyFileLog
        fields = ['id', 'subject', 'file_name', 'opened_at']