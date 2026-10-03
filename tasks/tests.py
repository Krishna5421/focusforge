from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Task


class TaskAjaxTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='task-user', password='pass12345')
        self.other_user = User.objects.create_user(username='other-user', password='pass12345')
        self.category = Category.objects.create(user=self.user, name='Work')
        self.client.login(username='task-user', password='pass12345')

    def test_ajax_create_saves_task_for_logged_in_user(self):
        response = self.client.post(reverse('tasks:ajax_task_create'), {
            'title': 'Write release notes',
            'category': self.category.pk,
            'priority': 'HIGH',
            'due_date': (timezone.localdate() + timedelta(days=7)).isoformat(),
            'tags': 'release, urgent',
        })

        self.assertEqual(response.status_code, 200)
        task = Task.objects.get(title='Write release notes')
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.priority, 'HIGH')
        self.assertEqual(list(task.tags.values_list('name', flat=True)), ['release', 'urgent'])

    def test_ajax_toggle_persists_completion(self):
        task = Task.objects.create(user=self.user, title='Complete me')

        response = self.client.post(reverse('tasks:ajax_toggle_status', args=[task.pk]))

        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, 'COMPLETED')
        self.assertIsNotNone(task.completed_at)

    def test_bulk_delete_only_deletes_current_users_tasks(self):
        own_task = Task.objects.create(user=self.user, title='My task')
        other_task = Task.objects.create(user=self.other_user, title='Other task')

        response = self.client.post(reverse('tasks:ajax_bulk_tasks'), {
            'action': 'delete',
            'task_ids[]': [own_task.pk, other_task.pk],
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(pk=own_task.pk).exists())
        self.assertTrue(Task.objects.filter(pk=other_task.pk).exists())

    def test_ajax_update_keeps_existing_overdue_date(self):
        overdue = timezone.now() - timedelta(days=3)
        task = Task.objects.create(user=self.user, title='Overdue', due_date=overdue)

        response = self.client.post(reverse('tasks:ajax_task_update', args=[task.pk]), {
            'title': 'Overdue renamed',
            'due_date': timezone.localtime(overdue).date().isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.title, 'Overdue renamed')

    def test_ajax_create_saves_selected_time(self):
        due_day = timezone.localdate() + timedelta(days=2)
        response = self.client.post(reverse('tasks:ajax_task_create'), {
            'title': 'Timed task', 'due_date': due_day.isoformat(), 'due_time': '15:30',
        })

        self.assertEqual(response.status_code, 200)
        due = timezone.localtime(Task.objects.get(title='Timed task').due_date)
        self.assertEqual((due.date(), due.hour, due.minute), (due_day, 15, 30))

    def test_ajax_create_without_time_is_due_end_of_day(self):
        due_day = timezone.localdate() + timedelta(days=2)
        self.client.post(reverse('tasks:ajax_task_create'), {'title': 'All day', 'due_date': due_day.isoformat()})

        due = timezone.localtime(Task.objects.get(title='All day').due_date)
        self.assertEqual((due.hour, due.minute), (23, 59))

    def test_ajax_create_rejects_time_without_date(self):
        response = self.client.post(reverse('tasks:ajax_task_create'), {'title': 'No date', 'due_time': '10:00'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('due date', response.json()['error'])

    def test_ajax_create_rejects_invalid_time(self):
        response = self.client.post(reverse('tasks:ajax_task_create'), {
            'title': 'Bad time', 'due_date': (timezone.localdate() + timedelta(days=1)).isoformat(), 'due_time': '25:99',
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Task.objects.filter(title='Bad time').exists())

    def test_ajax_create_rejects_time_that_already_passed(self):
        past = timezone.localtime(timezone.now() - timedelta(hours=2))
        response = self.client.post(reverse('tasks:ajax_task_create'), {
            'title': 'Too late', 'due_date': past.date().isoformat(), 'due_time': past.strftime('%H:%M'),
        })

        self.assertEqual(response.status_code, 400)

    def test_ajax_update_rejects_new_past_date(self):
        task = Task.objects.create(user=self.user, title='Upcoming')

        response = self.client.post(reverse('tasks:ajax_task_update', args=[task.pk]), {
            'title': 'Upcoming',
            'due_date': (timezone.localdate() - timedelta(days=1)).isoformat(),
        })

        self.assertEqual(response.status_code, 400)




class TaskDueReminderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reminder-user', password='pass12345')
        self.client.login(username='reminder-user', password='pass12345')

    def reminders(self, notification_type):
        from notifications.models import Notification
        return Notification.objects.filter(user=self.user, type=notification_type)

    def test_due_soon_reminder_is_sent_once(self):
        from .reminders import check_task_due_notifications
        Task.objects.create(user=self.user, title='Soon', due_date=timezone.now() + timedelta(minutes=30))

        self.assertEqual(check_task_due_notifications(self.user), 1)
        self.assertEqual(check_task_due_notifications(self.user), 0)
        self.assertEqual(self.reminders('TASK_DUE_SOON').count(), 1)

    def test_overdue_reminder_is_sent_once(self):
        from .reminders import check_task_due_notifications
        Task.objects.create(user=self.user, title='Late', due_date=timezone.now() - timedelta(minutes=5))

        check_task_due_notifications(self.user)
        check_task_due_notifications(self.user)
        self.assertEqual(self.reminders('TASK_OVERDUE').count(), 1)

    def test_rescheduled_task_is_reminded_again(self):
        from .reminders import check_task_due_notifications
        task = Task.objects.create(user=self.user, title='Moved', due_date=timezone.now() + timedelta(minutes=30))
        check_task_due_notifications(self.user)

        task.due_date = timezone.now() + timedelta(minutes=45)
        task.save()
        check_task_due_notifications(self.user)
        self.assertEqual(self.reminders('TASK_DUE_SOON').count(), 2)

    def test_completed_far_and_old_tasks_are_ignored(self):
        from .reminders import check_task_due_notifications
        Task.objects.create(user=self.user, title='Done', status='COMPLETED', due_date=timezone.now() - timedelta(minutes=5))
        Task.objects.create(user=self.user, title='Later', due_date=timezone.now() + timedelta(days=2))
        Task.objects.create(user=self.user, title='Ancient', due_date=timezone.now() - timedelta(days=30))
        Task.objects.create(user=self.user, title='No date')

        self.assertEqual(check_task_due_notifications(self.user), 0)

    def test_toast_endpoint_returns_task_reminders_once(self):
        Task.objects.create(user=self.user, title='Late', due_date=timezone.now() - timedelta(minutes=5))

        first = self.client.get(reverse('notifications:pending_toasts')).json()['notifications']
        second = self.client.get(reverse('notifications:pending_toasts')).json()['notifications']

        self.assertEqual([item['toast_type'] for item in first], ['error'])
        self.assertIn('Late', first[0]['message'])
        self.assertEqual(second, [])

    def test_toast_endpoint_survives_reminder_failure(self):
        from unittest import mock
        with mock.patch('tasks.reminders.check_task_due_notifications', side_effect=RuntimeError('boom')), \
                self.assertLogs('tasks.reminders', level='ERROR'):
            response = self.client.get(reverse('notifications:pending_toasts'))
        self.assertEqual(response.status_code, 200)

    def test_overdue_filter_uses_due_time(self):
        Task.objects.create(user=self.user, title='Earlier today', due_date=timezone.now() - timedelta(minutes=1))
        response = self.client.get(reverse('tasks:task_list'), {'filter': 'overdue'})
        self.assertContains(response, 'Earlier today')
        self.assertContains(response, 'task-due-flag')
