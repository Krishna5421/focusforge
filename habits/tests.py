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
            'name': 'Read daily', 'category': 'study', 'frequency': 'WEEKLY', 'target_days': '1,2,3',
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


class HabitScheduleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='planner', password='pass12345')
        self.client.login(username='planner', password='pass12345')
        self.today = timezone.localdate()

    def make(self, name, frequency='DAILY', target_days=None, days_old=60):
        habit = Habit.objects.create(user=self.user, name=name, frequency=frequency, target_days=target_days or [])
        Habit.objects.filter(pk=habit.pk).update(created_at=timezone.now() - timedelta(days=days_old))
        habit.refresh_from_db()
        return habit

    def test_only_scheduled_habits_count_as_due_today(self):
        from .schedule import annotate_habits
        weekday = self.today.isoweekday()
        other_day = weekday % 7 + 1
        daily = self.make('Daily walk')
        today_only = self.make('Today class', 'WEEKLY', [weekday])
        not_today = self.make('Other day class', 'WEEKLY', [other_day])
        HabitLog.objects.create(habit=daily, date=self.today, completed=True)

        habits, due_done, due_total = annotate_habits(self.user, self.today)
        by_name = {habit.name: habit for habit in habits}

        self.assertEqual((due_done, due_total), (1, 2))
        self.assertTrue(by_name['Today class'].due_today)
        self.assertFalse(by_name['Other day class'].due_today)
        self.assertEqual(by_name['Other day class'].next_day, self.today + timedelta(days=1))
        self.assertEqual(by_name['Daily walk'].schedule_label, 'Daily')

    def test_once_a_week_habit_is_not_due_after_being_done_this_week(self):
        from .schedule import annotate_habits, week_start
        weekly = self.make('Call parents', 'WEEKLY')
        habits, _, _ = annotate_habits(self.user, self.today)
        self.assertTrue(habits[0].due_today)
        self.assertEqual(habits[0].schedule_label, 'Once a week')

        if self.today != week_start(self.today):
            HabitLog.objects.create(habit=weekly, date=week_start(self.today), completed=True)
            habits, _, due_total = annotate_habits(self.user, self.today)
            self.assertFalse(habits[0].due_today)
            self.assertTrue(habits[0].done_this_week)
            self.assertEqual(due_total, 0)

    def test_completion_rate_uses_scheduled_days_in_last_30_days(self):
        from .schedule import completion_rate
        habit = self.make('Read')
        done = {self.today - timedelta(days=offset) for offset in range(15)}
        self.assertEqual(completion_rate(habit, done, self.today), 50)
        new_habit = self.make('New', days_old=0)
        self.assertEqual(completion_rate(new_habit, {self.today}, self.today), 100)

    def test_page_groups_habits_and_shows_summary(self):
        weekday = self.today.isoweekday()
        self.make('Due one')
        self.make('Later one', 'WEEKLY', [weekday % 7 + 1])
        response = self.client.get(reverse('habits:habit_list'))

        self.assertContains(response, 'Due today')
        self.assertContains(response, 'Not today')
        self.assertContains(response, '0 / 1 done today')
        self.assertContains(response, 'check-ins this month')

    def test_toggle_reports_due_progress_and_all_done(self):
        habit = self.make('Only one')
        data = self.client.post(reverse('habits:ajax_toggle_habit', args=[habit.pk])).json()
        self.assertEqual((data['due_done'], data['due_total'], data['all_done']), (1, 1, True))
        self.assertTrue(HabitLog.objects.filter(habit=habit, date=self.today).exists())

    def test_toggle_returns_live_month_summary(self):
        habit = self.make('Only one')
        data = self.client.post(reverse('habits:ajax_toggle_habit', args=[habit.pk])).json()
        self.assertEqual(data['month']['checkins'], 1)
        self.assertEqual(data['month']['best_count'], 1)
        self.assertGreater(data['month']['consistency'], 0)

        data = self.client.post(reverse('habits:ajax_toggle_habit', args=[habit.pk])).json()  # untick
        self.assertEqual(data['month']['checkins'], 0)
        self.assertEqual(data['month']['best_day_label'], '—')
