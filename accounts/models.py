from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    productivity_score = models.IntegerField(default=0)
    total_xp = models.IntegerField(default=0)

    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)

    email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_level(self):
        return self.total_xp // 100 + 1


class PasswordResetOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='password_reset_otp')
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at
