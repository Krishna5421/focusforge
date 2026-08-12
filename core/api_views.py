from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from datetime import timedelta

from tasks.models import Task
from habits.models import Habit
from study.models import Subject
from pomodoro.models import PomodoroSession
from goals.models import Goal
from django.utils import timezone


class TaskCompletionTrendAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        labels = []
        data = []

        day_count = 6
        while day_count >= 0:
            day = today - timedelta(days=day_count)
            completed_count = Task.objects.filter(user=user, status='COMPLETED', completed_at__date=day).count()
            labels.append(day.strftime('%a'))
            data.append(completed_count)
            day_count -= 1

        return Response({'labels': labels, 'data': data})


class HabitConsistencyAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        habits = Habit.objects.filter(user=request.user, is_active=True)
        labels = []
        data = []

        for habit in habits:
            labels.append(habit.name)
            data.append(habit.completion_rate())

        return Response({'labels': labels, 'data': data})


class StudyBreakdownAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subjects = Subject.objects.filter(user=request.user)
        labels = []
        data = []

        for subject in subjects:
            labels.append(subject.name)
            data.append(subject.total_hours())

        return Response({'labels': labels, 'data': data})


class FocusTimeTrendAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        labels = []
        data = []

        day_count = 6
        while day_count >= 0:
            day = today - timedelta(days=day_count)
            sessions = PomodoroSession.objects.filter(user=user, started_at__date=day, status='COMPLETED')
            total_seconds = 0
            for session in sessions:
                total_seconds += session.actual_focus_seconds
            labels.append(day.strftime('%a'))
            data.append(round(total_seconds / 60, 1))
            day_count -= 1

        return Response({'labels': labels, 'data': data})


class GoalProgressAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        goals = Goal.objects.filter(user=request.user, status='ACTIVE')
        labels = []
        data = []

        for goal in goals:
            labels.append(goal.title)
            data.append(goal.completion_percentage)

        return Response({'labels': labels, 'data': data})


class DashboardSummaryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = user.profile

        return Response({
            'total_xp': profile.total_xp,
            'level': profile.get_level(),
            'current_streak': profile.current_streak,
            'longest_streak': profile.longest_streak,
            'productivity_score': profile.productivity_score,
        })
        
class DashboardStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()

        todays_tasks_qs = Task.objects.filter(user=user, due_date__date=today)
        todays_tasks_count = todays_tasks_qs.count()
        completed_today_count = todays_tasks_qs.filter(status='COMPLETED').count()

        today_focus_seconds = 0
        todays_pomodoros = PomodoroSession.objects.filter(user=user, started_at__date=today, status='COMPLETED')
        for session in todays_pomodoros:
            today_focus_seconds += session.actual_focus_seconds
        today_focus_minutes = today_focus_seconds // 60

        active_goals_count = Goal.objects.filter(user=user, status='ACTIVE').count()
        profile = user.profile

        task_pct = 0
        if todays_tasks_count > 0:
            task_pct = round((completed_today_count / todays_tasks_count) * 100)

        return Response({
            'todays_tasks_count': todays_tasks_count,
            'completed_today_count': completed_today_count,
            'task_pct': task_pct,
            'current_streak': profile.current_streak,
            'today_focus_minutes': today_focus_minutes,
            'pomodoro_sessions_today': todays_pomodoros.count(),
            'active_goals_count': active_goals_count,
        })