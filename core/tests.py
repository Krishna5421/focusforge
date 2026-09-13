from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from goals.models import Goal
from habits.models import Habit, HabitLog
from pomodoro.models import PomodoroSession
from study.models import StudySession, Subject
from tasks.models import Task


class AnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analytics-user', password='password')
        self.other_user = User.objects.create_user(username='other-user', password='password')
        self.client.login(username='analytics-user', password='password')
        self.today = timezone.localdate()

    def test_analytics_uses_real_user_data(self):
        task = Task.objects.create(user=self.user, title='Complete report', status='COMPLETED', completed_at=timezone.now())
        PomodoroSession.objects.create(user=self.user, duration_minutes=25, actual_focus_seconds=1200, status='COMPLETED')
        habit = Habit.objects.create(user=self.user, name='Read')
        HabitLog.objects.create(habit=habit, date=self.today, completed=True)
        subject = Subject.objects.create(user=self.user, name='Mathematics')
        StudySession.objects.create(user=self.user, subject=subject, date=self.today, duration_minutes=20, actual_seconds=900)
        Goal.objects.create(user=self.user, title='Finish project', deadline=self.today, completion_percentage=60)
        PomodoroSession.objects.create(user=self.other_user, duration_minutes=25, actual_focus_seconds=1500, status='COMPLETED')

        response = self.client.get(reverse('core:analytics_data'), {'period': 'week'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['labels']), 7)
        self.assertEqual(data['focus']['actual'][-1], 20)
        self.assertEqual(data['focus']['planned'][-1], 25)
        self.assertEqual(data['tasks'][-1], 1)
        self.assertEqual(data['habits'][-1], 100)
        self.assertEqual(data['study']['labels'], ['Mathematics'])
        self.assertEqual(data['study']['data'], [15])
        self.assertEqual(data['goals']['data'], [60])
