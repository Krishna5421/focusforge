from django import forms
from .models import Task, Category, Tag

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'category', 'priority', 'status',
            'due_date', 'parent_task', 'is_repeating', 'repeat_frequency'
            # ⚠️ 'tags' is intentionally removed from here
        ]
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)
            # ⚠️ Removed tags queryset line
            self.fields['parent_task'].queryset = Task.objects.filter(user=user, parent_task__isnull=True)