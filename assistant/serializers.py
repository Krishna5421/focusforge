from rest_framework import serializers
from .models import AIQueryLog


class AIQueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQueryLog
        fields = ['id', 'query', 'response', 'created_at']