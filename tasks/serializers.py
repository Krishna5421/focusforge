from rest_framework import serializers
from .models import Task, Category, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'color']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class TaskSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    subtask_progress = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'category', 'category_name', 'tags',
            'priority', 'status', 'due_date', 'parent_task', 'is_repeating',
            'repeat_frequency', 'completed_at', 'created_at', 'updated_at',
            'subtask_progress'
        ]
        read_only_fields = ['completed_at', 'created_at', 'updated_at']

    def get_subtask_progress(self, obj):
        return obj.subtask_progress()