from django.contrib.auth.models import User
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from unittest.mock import Mock, patch

from .emailing import send_brevo_email
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


class BrevoEmailTests(TestCase):
    @override_settings(
        BREVO_API_KEY='test-api-key',
        BREVO_SENDER_EMAIL='sender@example.com',
        BREVO_SENDER_NAME='FocusForge',
    )
    @patch('notifications.emailing.requests.post')
    def test_brevo_payload_uses_html_and_plain_text(self, post):
        response = Mock()
        post.return_value = response

        sent = send_brevo_email(
            'recipient@example.com',
            'FocusForge test',
            '<p>Hello</p>',
            'Hello',
        )

        self.assertTrue(sent)
        post.assert_called_once_with(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'accept': 'application/json',
                'api-key': 'test-api-key',
                'content-type': 'application/json',
            },
            json={
                'sender': {'email': 'sender@example.com', 'name': 'FocusForge'},
                'to': [{'email': 'recipient@example.com'}],
                'subject': 'FocusForge test',
                'htmlContent': '<p>Hello</p>',
                'textContent': 'Hello',
            },
            timeout=10,
        )
        response.raise_for_status.assert_called_once_with()
