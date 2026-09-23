from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'bio', 'profile_picture', 'productivity_score', 'total_xp',
            'current_streak', 'longest_streak', 'email_verified'
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def validate_email(self, value):
        email = value.strip()
        existing_users = User.objects.filter(email__iexact=email)
        if self.instance:
            existing_users = existing_users.exclude(pk=self.instance.pk)
        if email and existing_users.exists():
            raise serializers.ValidationError('This email is already registered. Please use a different email or log in.')
        return email

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        return user
