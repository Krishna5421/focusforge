from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Habit, HabitLog


class HabitLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitLog
        fields = ['id', 'habit', 'date', 'completed']


class HabitSerializer(serializers.ModelSerializer):
    completion_rate = serializers.SerializerMethodField()
    target_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7),
        required=False,
        allow_empty=True,
    )

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

    def validate_target_days(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Choose each weekday only once.')
        return sorted(value)

    def validate(self, attrs):
        frequency = attrs.get('frequency', getattr(self.instance, 'frequency', 'DAILY'))
        target_days = attrs.get('target_days', getattr(self.instance, 'target_days', []))
        if frequency == 'DAILY' and target_days:
            raise ValidationError({
                'target_days': 'Target days only apply to weekly habits. Choose Weekly or clear the selected days.'
            })
        return attrs
