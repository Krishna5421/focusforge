from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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
            'due_date': '2026-09-04',
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

# Create your tests here.
