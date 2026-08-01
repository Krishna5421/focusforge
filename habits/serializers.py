from rest_framework import serializers
from .models import Habit, HabitLog


class HabitLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitLog
        fields = ['id', 'habit', 'date', 'completed']


class HabitSerializer(serializers.ModelSerializer):
    completion_rate = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            'id', 'name', 'icon', 'frequency', 'target_days',
            'current_streak', 'longest_streak', 'is_active',
            'created_at', 'completion_rate'
        ]
        read_only_fields = ['current_streak', 'longest_streak']

    def get_completion_rate(self, obj):
        return obj.completion_rate()