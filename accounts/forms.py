from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'John'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Doe'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'forge_master'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': '8+ characters'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Repeat password'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if username.startswith('_'):
            raise forms.ValidationError('Username cannot start with an underscore.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already in use. Please choose another one.')
        return username


class StyledLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}))


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell us a little about yourself.',
            }),
            'profile_picture': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.exclude(pk=self.instance.pk).filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already in use.')
        return username


class PasswordResetRequestForm(forms.Form):
    identifier = forms.CharField(label='Username or email', max_length=254,
        widget=forms.TextInput(attrs={'placeholder': 'Enter username or email', 'autocomplete': 'username'}))


class PasswordResetOTPForm(forms.Form):
    otp = forms.CharField(label='6-digit code', min_length=6, max_length=6,
        widget=forms.TextInput(attrs={'placeholder': '000000', 'inputmode': 'numeric', 'autocomplete': 'one-time-code'}))

    def clean_otp(self):
        otp = self.cleaned_data['otp'].strip()
        if not otp.isdigit():
            raise forms.ValidationError('Enter the 6-digit code from your email.')
        return otp


class PasswordResetSetForm(forms.Form):
    new_password1 = forms.CharField(label='New password', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    new_password2 = forms.CharField(label='Confirm new password', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password1') != cleaned.get('new_password2'):
            self.add_error('new_password2', 'Passwords do not match.')
        if cleaned.get('new_password1') and len(cleaned['new_password1']) < 8:
            self.add_error('new_password1', 'Use at least 8 characters.')
        return cleaned
