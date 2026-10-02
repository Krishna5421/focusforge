from django import forms
from .models import Habit


class HabitForm(forms.ModelForm):
    target_days = forms.MultipleChoiceField(
        required=False,
        choices=[(1, 'Monday (1)'), (2, 'Tuesday (2)'), (3, 'Wednesday (3)'),
                 (4, 'Thursday (4)'), (5, 'Friday (5)'), (6, 'Saturday (6)'),
                 (7, 'Sunday (7)')],
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Habit
        fields = ['name', 'category', 'frequency', 'target_days']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Read for 30 mins'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.target_days:
            self.initial['target_days'] = [str(day) for day in self.instance.target_days]

    def clean_target_days(self):
        return sorted({int(day) for day in self.cleaned_data.get('target_days', [])})

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('frequency') == 'DAILY' and cleaned_data.get('target_days'):
            self.add_error(
                'target_days',
                'Target days only apply to weekly habits. Choose Weekly or clear the selected days.',
            )
        return cleaned_data
