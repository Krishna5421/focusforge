"""Admin for accounts: manage users without exposing their personal content.

Users' tasks, habits, goals, study notes, focus history, notifications and AI chats are deliberately
not registered in the admin. Staff see only what's needed for support: account details, status,
XP and per-user activity counts (never titles, descriptions, notes or chat text).
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html_join

from assistant.models import AIQueryLog
from goals.models import Goal
from habits.models import Habit
from pomodoro.models import PomodoroSession
from study.models import StudySession
from tasks.models import Task
from .models import Profile


class UserAdmin(DjangoUserAdmin):
    readonly_fields = ('activity_summary', 'last_login', 'date_joined')
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Activity (counts only — content is private)', {'fields': ('activity_summary',)}),
    )

    @admin.display(description='Activity')
    def activity_summary(self, user):
        if not user.pk:
            return '—'
        counts = (
            ('Tasks', Task.objects.filter(user=user).count()),
            ('Habits', Habit.objects.filter(user=user).count()),
            ('Goals', Goal.objects.filter(user=user).count()),
            ('Focus sessions', PomodoroSession.objects.filter(user=user).count()),
            ('Study sessions', StudySession.objects.filter(user=user).count()),
            ('AI questions', AIQueryLog.objects.filter(user=user).count()),
        )
        return format_html_join(' · ', '{}: <strong>{}</strong>', counts)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # Bio and profile photo are personal, so they are left out entirely.
    fields = ('user', 'level', 'total_xp', 'current_streak', 'longest_streak', 'email_verified', 'created_at')
    readonly_fields = ('user', 'level', 'total_xp', 'current_streak', 'longest_streak', 'created_at')
    list_display = ('user', 'level', 'total_xp', 'current_streak', 'email_verified', 'created_at')
    list_filter = ('email_verified',)
    search_fields = ('user__username', 'user__email')

    @admin.display(description='Level')
    def level(self, profile):
        return profile.get_level()

    def has_add_permission(self, request):
        return False  # Profiles are created automatically with each user.
