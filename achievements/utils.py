from .models import Achievement, UserAchievement
from tasks.models import Task
from habits.models import Habit
from goals.models import Goal
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


def unlock_achievement(user, achievement):
    already_unlocked = UserAchievement.objects.filter(user=user, achievement=achievement).exists()
    if not already_unlocked:
        UserAchievement.objects.create(user=user, achievement=achievement)
        profile = user.profile
        profile.total_xp += achievement.xp_reward
        profile.save()
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


def check_focus_achievements(user):
    sessions = PomodoroSession.objects.filter(user=user, status='COMPLETED')
    total_seconds = 0
    for session in sessions:
        total_seconds += session.actual_focus_seconds

    total_hours = total_seconds / 3600
    achievements = Achievement.objects.filter(criteria_type='FOCUS_HOURS')

    for achievement in achievements:
        if total_hours >= achievement.criteria_value:
            unlock_achievement(user, achievement)


def check_all_achievements(user):
    check_task_achievements(user)
    check_streak_achievements(user)
    check_goal_achievements(user)
    check_study_achievements(user)
    check_focus_achievements(user)