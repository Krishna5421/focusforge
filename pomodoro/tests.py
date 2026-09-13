from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from tasks.models import Task
from .models import PomodoroSession, PomodoroSettings


class PomodoroViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='focus-user', password='password')
        self.other_user = User.objects.create_user(username='other-user', password='password')
        self.task = Task.objects.create(user=self.user, title='Write project notes')
        self.client.login(username='focus-user', password='password')

    def test_start_saves_the_selected_users_task(self):
        response = self.client.post(reverse('pomodoro:pomodoro_start'), {
            'task_id': self.task.id,
            'duration': 25,
        })

        self.assertEqual(response.status_code, 200)
        session = PomodoroSession.objects.get(pk=response.json()['session_id'])
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.task, self.task)
        self.assertEqual(session.status, 'RUNNING')

    def test_start_cannot_attach_another_users_task(self):
        foreign_task = Task.objects.create(user=self.other_user, title='Private task')
        response = self.client.post(reverse('pomodoro:pomodoro_start'), {
            'task_id': foreign_task.id,
            'duration': 25,
        })

        self.assertEqual(response.status_code, 404)
        self.assertFalse(PomodoroSession.objects.filter(user=self.user).exists())

    def test_completion_updates_stored_session(self):
        session = PomodoroSession.objects.create(user=self.user, task=self.task, duration_minutes=25)
        response = self.client.post(reverse('pomodoro:pomodoro_update', args=[session.id]), {
            'status': 'COMPLETED',
            'focus_seconds': 1500,
        })

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, 'COMPLETED')
        self.assertEqual(session.actual_focus_seconds, 1500)
        self.assertIsNotNone(session.completed_at)

    def test_daily_goal_is_saved_for_the_user(self):
        response = self.client.post(reverse('pomodoro:update_daily_goal'), {'daily_goal': 8})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['daily_goal'], 8)
        self.assertEqual(PomodoroSettings.objects.get(user=self.user).daily_goal, 8)

    def test_today_statistics_exclude_yesterdays_sessions(self):
        PomodoroSession.objects.create(
            user=self.user, status='COMPLETED', duration_minutes=25, actual_focus_seconds=1500,
        )
        yesterday_session = PomodoroSession.objects.create(
            user=self.user, status='COMPLETED', duration_minutes=25, actual_focus_seconds=1500,
        )
        PomodoroSession.objects.filter(pk=yesterday_session.pk).update(
            started_at=timezone.now() - timedelta(days=1)
        )

        response = self.client.get(reverse('pomodoro:pomodoro_page'))

        self.assertEqual(response.context['completed_today'], 1)
        self.assertEqual(response.context['today_focus_minutes'], 25)
        self.assertEqual(response.context['recent_sessions'][0].started_at.date(), timezone.localdate())
        self.assertTrue(PomodoroSettings.objects.filter(user=self.user).exists())
