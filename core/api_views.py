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