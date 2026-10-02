from .models import Achievement, UserAchievement
from tasks.models import Task
from habits.models import Habit, HabitLog
from goals.models import Goal, Milestone
from study.models import StudySession
from pomodoro.models import PomodoroSession


XP_VALUES = {
    'TASK_COMPLETED': 10,
    'HABIT_CHECKIN': 5,
    'POMODORO_COMPLETED': 15,
    'STUDY_SESSION_LOGGED': 10,
    'MILESTONE_COMPLETED': 20,
    'GOAL_COMPLETED': 50,
}


def award_xp(user, action_type):
    amount = XP_VALUES.get(action_type, 0)
    profile = user.profile
    profile.total_xp += amount
    profile.save()
    return amount


def remove_xp(user, action_type):
    amount = XP_VALUES.get(action_type, 0)
    profile = user.profile
    profile.total_xp = max(0, profile.total_xp - amount)
    profile.save(update_fields=['total_xp', 'updated_at'])
    return amount


def unlock_achievement(user, achievement):
    already_unlocked = UserAchievement.objects.filter(user=user, achievement=achievement).exists()
    if not already_unlocked:
        UserAchievement.objects.create(user=user, achievement=achievement)
        profile = user.profile
        profile.total_xp += achievement.xp_reward
        profile.save()
        from notifications.utils import notify_once
        notification = notify_once(user, 'ACHIEVEMENT_UNLOCKED', 'Achievement unlocked!',
                                   f'{achievement.name} · +{achievement.xp_reward} XP earned.', achievement.pk)
        from notifications.models import Notification
        Notification.objects.filter(pk=notification.pk).update(toast_pending=True)
        return True
    return False


def check_task_achievements(user):
    completed_count = Task.objects.filter(user=user, status='COMPLETED').count()
    achievements = Achievement.objects.filter(criteria_type='TASKS_COMPLETED')

    for achievement in achievements:
        if completed_count >= achievement.criteria_value:
            unlock_achievement(user, achievement)


def check_streak_achievements(user):
    habits = Habit.objects.filter(user=user)
    highest_streak = 0
    for habit in habits:
        if habit.current_streak > highest_streak:
            highest_streak = habit.current_streak

    achievements = Achievement.objects.filter(criteria_type='STREAK')
    for achievement in achievements:
        if highest_streak >= achievement.criteria_value:
            unlock_achievement(user, achievement)


def check_habit_checkin_achievements(user):
    completed_checkins = HabitLog.objects.filter(habit__user=user, completed=True).count()
    for achievement in Achievement.objects.filter(criteria_type='HABIT_CHECKINS'):
        if completed_checkins >= achievement.criteria_value:
            unlock_achievement(user, achievement)


def check_milestone_achievements(user):
    completed_milestones = Milestone.objects.filter(goal__user=user, is_completed=True).count()
    for achievement in Achievement.objects.filter(criteria_type='MILESTONES_COMPLETED'):
        if completed_milestones >= achievement.criteria_value:
            unlock_achievement(user, achievement)


def check_goal_achievements(user):
    completed_count = Goal.objects.filter(user=user, status='COMPLETED').count()
    achievements = Achievement.objects.filter(criteria_type='GOALS_COMPLETED')

    for achievement in achievements:
        if completed_count >= achievement.criteria_value:
            unlock_achievement(user, achievement)


def check_study_achievements(user):
    session_count = StudySession.objects.filter(user=user).count()
    achievements = Achievement.objects.filter(criteria_type='STUDY_SESSIONS')

    for achievement in achievements:
        if session_count >= achievement.criteria_value:
            unlock_achievement(user, achievement)

    study_minutes = sum(StudySession.objects.filter(user=user).values_list('duration_minutes', flat=True))
    for achievement in Achievement.objects.filter(criteria_type='STUDY_MINUTES'):
        if study_minutes >= achievement.criteria_value:
            unlock_achievement(user, achievement)


def check_focus_achievements(user):
    sessions = PomodoroSession.objects.filter(user=user, status='COMPLETED')
    completed_session_count = sessions.count()
    total_seconds = 0
    for session in sessions:
        total_seconds += session.actual_focus_seconds

    total_hours = total_seconds / 3600
    achievements = Achievement.objects.filter(criteria_type='FOCUS_HOURS')

    for achievement in achievements:
        if total_hours >= achievement.criteria_value:
            unlock_achievement(user, achievement)

    for achievement in Achievement.objects.filter(criteria_type='FOCUS_SESSIONS'):
        if completed_session_count >= achievement.criteria_value:
            unlock_achievement(user, achievement)


def check_all_achievements(user):
    check_task_achievements(user)
    check_streak_achievements(user)
    check_habit_checkin_achievements(user)
    check_goal_achievements(user)
    check_milestone_achievements(user)
    check_study_achievements(user)
    check_focus_achievements(user)
