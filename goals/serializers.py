from rest_framework import serializers
from django.utils import timezone
from .models import Goal, Milestone


class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = ['id', 'goal', 'title', 'is_completed', 'completed_at', 'order']
        read_only_fields = ['completed_at']


class GoalSerializer(serializers.ModelSerializer):
    milestone_progress = serializers.SerializerMethodField()
    milestones = MilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id', 'title', 'description', 'deadline', 'completion_percentage',
            'status', 'created_at', 'milestone_progress', 'milestones'
        ]
        read_only_fields = ['completion_percentage', 'status']

    def validate_deadline(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError('Choose today or a future deadline.')
        return value

    def get_milestone_progress(self, obj):
        return obj.milestone_progress()
