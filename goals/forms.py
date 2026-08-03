from django import forms
from .models import Goal, Milestone


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['title', 'description', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['title', 'order']