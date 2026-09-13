from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Achievement, UserAchievement
from .utils import check_all_achievements
from tasks.models import Task
from habits.models import Habit
from goals.models import Goal
from study.models import StudySession
from pomodoro.models import PomodoroSession


@login_required
def achievement_list(request):
    check_all_achievements(request.user)
    user = request.user
    highest_streak = max((habit.current_streak for habit in Habit.objects.filter(user=user)), default=0)
    focus_seconds = sum(session.actual_focus_seconds for session in PomodoroSession.objects.filter(user=user, status='COMPLETED'))
    progress_values = {
        'TASKS_COMPLETED': Task.objects.filter(user=user, status='COMPLETED').count(),
        'STREAK': highest_streak,
        'FOCUS_HOURS': focus_seconds / 3600,
        'STUDY_SESSIONS': StudySession.objects.filter(user=user).count(),
        'GOALS_COMPLETED': Goal.objects.filter(user=user, status='COMPLETED').count(),
    }
    labels = {
        'TASKS_COMPLETED': 'tasks', 'STREAK': 'day streak', 'FOCUS_HOURS': 'focus hours',
        'STUDY_SESSIONS': 'study sessions', 'GOALS_COMPLETED': 'goals',
    }
    unlocked_ids = set(UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True))
    unlocked, locked = [], []
    for achievement in Achievement.objects.all().order_by('criteria_type', 'criteria_value'):
        current = progress_values[achievement.criteria_type]
        display_current = round(current, 1) if achievement.criteria_type == 'FOCUS_HOURS' else int(current)
        item = {
            'achievement': achievement,
            'current': display_current,
            'remaining': max(0, achievement.criteria_value - display_current),
            'unit': labels[achievement.criteria_type],
            'percent': min(100, round((current / achievement.criteria_value) * 100)) if achievement.criteria_value else 0,
        }
        (unlocked if achievement.id in unlocked_ids else locked).append(item)

    profile = user.profile
    level = profile.get_level()
    xp_for_next_level = level * 100 - profile.total_xp
    return render(request, 'achievements/achievement_list.html', {
        'unlocked': unlocked,
        'locked': locked,
        'xp_to_next_level': xp_for_next_level,
        'xp_level_progress': profile.total_xp % 100,
        'next_level': level + 1,
    })
