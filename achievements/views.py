from collections import Counter

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from .models import Achievement, UserAchievement
from .utils import check_all_achievements
from tasks.models import Task
from habits.models import Habit, HabitLog
from goals.models import Goal, Milestone
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
        'HABIT_CHECKINS': HabitLog.objects.filter(habit__user=user, completed=True).count(),
        'MILESTONES_COMPLETED': Milestone.objects.filter(goal__user=user, is_completed=True).count(),
        'FOCUS_SESSIONS': PomodoroSession.objects.filter(user=user, status='COMPLETED').count(),
        'STUDY_MINUTES': StudySession.objects.filter(user=user).aggregate(total=Sum('duration_minutes'))['total'] or 0,
    }
    labels = {
        'TASKS_COMPLETED': 'tasks', 'STREAK': 'day streak', 'FOCUS_HOURS': 'focus hours',
        'STUDY_SESSIONS': 'study sessions', 'GOALS_COMPLETED': 'goals',
        'HABIT_CHECKINS': 'habit check-ins', 'MILESTONES_COMPLETED': 'milestones',
        'FOCUS_SESSIONS': 'focus sessions', 'STUDY_MINUTES': 'study minutes',
    }
    unlocked_ids = set(UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True))
    unlocked, locked = [], []
    category_keys = {
        'TASKS_COMPLETED': 'tasks',
        'STREAK': 'habits',
        'FOCUS_HOURS': 'focus',
        'STUDY_SESSIONS': 'study',
        'GOALS_COMPLETED': 'goals',
        'HABIT_CHECKINS': 'habits',
        'MILESTONES_COMPLETED': 'goals',
        'FOCUS_SESSIONS': 'focus',
        'STUDY_MINUTES': 'study',
    }
    category_labels = {
        'TASKS_COMPLETED': 'Tasks',
        'STREAK': 'Habits',
        'FOCUS_HOURS': 'Focus',
        'STUDY_SESSIONS': 'Study',
        'GOALS_COMPLETED': 'Goals',
        'HABIT_CHECKINS': 'Habits',
        'MILESTONES_COMPLETED': 'Goals',
        'FOCUS_SESSIONS': 'Focus',
        'STUDY_MINUTES': 'Study',
    }

    def compact_duration(total_minutes):
        hours, minutes = divmod(total_minutes, 60)
        if hours and minutes:
            return f'{hours}h {minutes}m'
        if hours:
            return f'{hours}h'
        return f'{minutes}m'

    for achievement in Achievement.objects.all().order_by('criteria_type', 'criteria_value'):
        current = progress_values[achievement.criteria_type]
        display_current = int(current)
        target = achievement.criteria_value
        if achievement.criteria_type == 'STREAK':
            target_description = f'Maintain a {target}-day habit streak'
        elif achievement.criteria_type == 'FOCUS_HOURS':
            target_description = f'Complete {target} total focus hours'
        elif achievement.criteria_type == 'STUDY_SESSIONS':
            target_description = f'Complete {target} study sessions'
        elif achievement.criteria_type == 'GOALS_COMPLETED':
            target_description = f'Complete {target} goals'
        elif achievement.criteria_type == 'HABIT_CHECKINS':
            target_description = f'Check in to habits {target} times'
        elif achievement.criteria_type == 'MILESTONES_COMPLETED':
            target_description = f'Complete {target} goal milestones'
        elif achievement.criteria_type == 'FOCUS_SESSIONS':
            target_description = f'Complete {target} focus sessions'
        elif achievement.criteria_type == 'STUDY_MINUTES':
            target_description = f'Log {target} minutes of study time'
        else:
            target_description = f'Complete {target} tasks'
        if achievement.criteria_type == 'FOCUS_HOURS':
            focused_minutes = focus_seconds // 60
            target_minutes = target * 60
            remaining_minutes = max(0, target_minutes - focused_minutes)
            progress_text = (
                f'{compact_duration(focused_minutes)} / {compact_duration(target_minutes)} · '
                f'{compact_duration(remaining_minutes)} to unlock'
            )
        elif achievement.criteria_type == 'STUDY_MINUTES':
            current_minutes = int(current)
            progress_text = (
                f'{compact_duration(current_minutes)} / {compact_duration(target)} · '
                f'{compact_duration(max(0, target - current_minutes))} to unlock'
            )
        else:
            progress_units = {
                'TASKS_COMPLETED': 'tasks',
                'STREAK': 'days',
                'STUDY_SESSIONS': 'study sessions',
                'GOALS_COMPLETED': 'goals',
                'HABIT_CHECKINS': 'check-ins',
                'MILESTONES_COMPLETED': 'milestones',
                'FOCUS_SESSIONS': 'focus sessions',
            }
            unit = progress_units[achievement.criteria_type]
            progress_text = (
                f'{display_current} / {target} {unit} · '
                f'{max(0, target - display_current)} more {unit} to unlock'
            )
        item = {
            'achievement': achievement,
            'current': display_current,
            'remaining': max(0, achievement.criteria_value - display_current),
            'unit': labels[achievement.criteria_type],
            'category_key': category_keys[achievement.criteria_type],
            'category_label': category_labels[achievement.criteria_type],
            'target_description': target_description,
            'progress_text': progress_text,
            'is_unlocked': achievement.id in unlocked_ids,
            'percent': min(100, round((current / achievement.criteria_value) * 100)) if achievement.criteria_value else 0,
        }
        (unlocked if achievement.id in unlocked_ids else locked).append(item)

    catalog = sorted(unlocked + locked, key=lambda item: (
        ['focus', 'study', 'habits', 'tasks', 'goals'].index(item['category_key']),
        item['achievement'].criteria_value,
    ))

    profile = user.profile
    level = profile.get_level()
    xp_for_next_level = level * 100 - profile.total_xp
    return render(request, 'achievements/achievement_list.html', {
        'unlocked': unlocked,
        'locked': locked,
        'catalog': catalog,
        'category_counts': Counter(item['category_key'] for item in catalog),
        'xp_to_next_level': xp_for_next_level,
        'xp_level_progress': profile.total_xp % 100,
        'next_level': level + 1,
    })
