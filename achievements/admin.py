from django.contrib import admin

from .models import Achievement, UserAchievement


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    # The achievement catalog is app content, so it stays fully editable.
    list_display = ('name', 'icon', 'criteria_type', 'criteria_value', 'xp_reward')
    list_filter = ('criteria_type',)
    search_fields = ('name',)


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    # Who unlocked what is shown for support, but can't be changed by hand.
    list_display = ('user', 'achievement', 'unlocked_at')
    list_filter = ('achievement__criteria_type',)
    search_fields = ('user__username',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
