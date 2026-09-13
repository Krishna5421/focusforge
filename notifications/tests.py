from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Notification


class NotificationPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='notified-user', password='password')
        self.client.login(username='notified-user', password='password')

    def test_feed_and_mark_all_read_are_user_scoped(self):
        notification = Notification.objects.create(
            user=self.user, type='TASK_COMPLETED', title='Task completed', message='You completed a task.'
        )
        other = User.objects.create_user(username='other-user', password='password')
        Notification.objects.create(user=other, type='FOCUS_COMPLETED', title='Other', message='Private')

        response = self.client.get(reverse('notifications:notification_list'))
        self.assertContains(response, 'Task completed')
        self.assertNotContains(response, 'Private')

        response = self.client.post(reverse('notifications:notification_mark_all_read'))
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

        response = self.client.post(reverse('notifications:notification_clear_all'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Notification.objects.filter(user=self.user).exists())
        self.assertTrue(Notification.objects.filter(user=other).exists())
