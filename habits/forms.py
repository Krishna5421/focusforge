from django import forms
from .models import Habit


class HabitForm(forms.ModelForm):
    target_days = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., 1,2,3,4,5 (Mon-Fri) or leave blank for every day'
        })
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
            self.initial['target_days'] = ','.join(str(d) for d in self.instance.target_days)

    def clean_target_days(self):
        value = self.cleaned_data.get('target_days', '')
        if not value:
            return []
        days = []
        for part in value.split(','):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= 7:
                days.append(int(part))
        return days