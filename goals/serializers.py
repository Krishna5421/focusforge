from rest_framework import serializers
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

    def get_milestone_progress(self, obj):
        return obj.milestone_progress()