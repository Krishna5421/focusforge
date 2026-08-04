from django import forms
from .models import Subject, StudySession


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'color']


class StudySessionForm(forms.ModelForm):
    class Meta:
        model = StudySession
        fields = ['subject', 'date', 'duration_minutes', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(user=user)