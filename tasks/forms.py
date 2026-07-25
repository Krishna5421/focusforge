from django import forms
from .models import Task, Category, Tag


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'category', 'tags', 'priority', 'status',
            'due_date', 'parent_task', 'is_repeating', 'repeat_frequency'
        ]
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)
            self.fields['tags'].queryset = Tag.objects.filter(user=user)
            self.fields['parent_task'].queryset = Task.objects.filter(user=user, parent_task__isnull=True)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'color']


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']