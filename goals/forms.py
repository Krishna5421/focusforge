from django import forms
from django.utils import timezone
from .models import Goal, Milestone


class GoalForm(forms.ModelForm):
    milestones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Add one milestone per line',
            'class': 'form-textarea',
        }),
    )

    class Meta:
        model = Goal
        fields = ['title', 'description', 'deadline', 'milestones']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['deadline'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_deadline(self):
        deadline = self.cleaned_data['deadline']
        if deadline < timezone.localdate():
            raise forms.ValidationError('Choose today or a future date.')
        return deadline

    def clean_milestones(self):
        titles = [line.strip() for line in self.cleaned_data['milestones'].splitlines() if line.strip()]
        if not titles:
            raise forms.ValidationError('Add at least one milestone so you have a clear first step toward your goal.')
        return titles


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['title', 'order']
