from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Habit, HabitLog


class HabitAjaxTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='habit-user', password='pass12345')
        self.other_user = User.objects.create_user(username='other-user', password='pass12345')
        self.client.login(username='habit-user', password='pass12345')

    def test_ajax_create_creates_habit_for_current_user(self):
        response = self.client.post(reverse('habits:ajax_habit_create'), {
            'name': 'Read daily', 'category': 'study', 'frequency': 'DAILY', 'target_days': '1,2,3',
        })
        self.assertEqual(response.status_code, 200)
        habit = Habit.objects.get(name='Read daily')
        self.assertEqual(habit.user, self.user)
        self.assertEqual(habit.target_days, [1, 2, 3])

    def test_toggle_updates_log_and_streak(self):
        habit = Habit.objects.create(user=self.user, name='Walk')
        response = self.client.post(reverse('habits:ajax_toggle_habit', args=[habit.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['completed'])
        self.assertTrue(HabitLog.objects.filter(habit=habit, date=timezone.localdate()).exists())
        habit.refresh_from_db()
        self.assertEqual(habit.current_streak, 1)

    def test_delete_only_deactivates_own_habit(self):
        habit = Habit.objects.create(user=self.user, name='Own habit')
        other_habit = Habit.objects.create(user=self.other_user, name='Other habit')
        response = self.client.post(reverse('habits:ajax_habit_delete', args=[habit.pk]))
        self.assertEqual(response.status_code, 200)
        habit.refresh_from_db()
        self.assertFalse(habit.is_active)
        other_habit.refresh_from_db()
        self.assertTrue(other_habit.is_active)

    def test_streak_resets_when_latest_completion_is_old(self):
        habit = Habit.objects.create(user=self.user, name='Old habit')
        HabitLog.objects.create(habit=habit, date=timezone.localdate() - timedelta(days=2))
        habit.refresh_from_db()
        self.assertEqual(habit.current_streak, 0)

# Create your tests here.
