from django.contrib.auth.models import User
from django.test import TestCase, override_settings
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


class ErrorHandlingTests(TestCase):
    @override_settings(DEBUG=False)
    def test_missing_page_shows_safe_error_page(self):
        response = self.client.get('/this-page-does-not-exist/')

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found', status_code=404)

    @override_settings(DEBUG=False)
    def test_missing_api_route_returns_safe_json_error(self):
        response = self.client.get('/api/does-not-exist/', HTTP_ACCEPT='application/json')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'The page you requested does not exist or may have moved.')


class GlobalSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='search-user', password='password')
        self.other_user = User.objects.create_user(username='other-search-user', password='password')
        self.client.login(username='search-user', password='password')

    def test_search_opens_the_matching_tasks_page(self):
        Task.objects.create(user=self.user, title='Read project brief')
        Task.objects.create(user=self.other_user, title='Read private notes')

        response = self.client.get(reverse('core:global_search'), {'q': 'Read'}, follow=True)

        self.assertEqual(response.redirect_chain[-1][0], f'{reverse("tasks:task_list")}?search=Read')
        self.assertContains(response, 'Read project brief')
        self.assertNotContains(response, 'Read private notes')
        self.assertContains(response, 'Matching results found for')

    def test_search_opens_the_matching_habits_page(self):
        Habit.objects.create(user=self.user, name='Read every day')

        response = self.client.get(reverse('core:global_search'), {'q': 'Read'}, follow=True)

        self.assertEqual(response.redirect_chain[-1][0], f'{reverse("habits:habit_list")}?search=Read')
        self.assertContains(response, 'Read every day')

    def test_search_opens_the_matching_goals_page(self):
        Goal.objects.create(user=self.user, title='Read twelve books', deadline=timezone.localdate())

        response = self.client.get(reverse('core:global_search'), {'q': 'Read'}, follow=True)

        self.assertEqual(response.redirect_chain[-1][0], f'{reverse("goals:goal_list")}?search=Read')
        self.assertContains(response, 'Read twelve books')

    def test_search_shows_friendly_empty_state(self):
        response = self.client.get(reverse('core:global_search'), {'q': 'nothing-matches-this'}, follow=True)

        self.assertContains(response, 'No tasks, habits, or goals were found')
