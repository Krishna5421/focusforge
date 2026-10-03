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

    def test_feed_includes_clear_confirmation_modal(self):
        Notification.objects.create(user=self.user, type='TASK_COMPLETED', title='Done', message='Completed.')

        response = self.client.get(reverse('notifications:notification_list'))

        self.assertContains(response, 'Clear all notifications?')
        self.assertContains(response, 'confirmClearNotifications')


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


@override_settings(SITE_URL='https://focusforge.onrender.com')
class EmailLayoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('mailer', email='mailer@example.com', password='x', first_name='Riya')

    def test_links_are_absolute_and_text_version_is_clean(self):
        from .emailing import render_focusforge_email
        html, text = render_focusforge_email(
            self.user, 'Subject', 'Heading', 'Body text.', '/tasks/', action_label='View your tasks',
            details=[('Time', 'Oct 2')], secondary_text='Not you?', secondary_label='Reset', secondary_url='/accounts/password-reset/',
        )
        self.assertIn('href="https://focusforge.onrender.com/tasks/"', html)
        self.assertIn('View your tasks', html)
        self.assertNotIn('<img', html)
        self.assertIn('View your tasks: https://focusforge.onrender.com/tasks/', text)
        self.assertIn('Not you? Reset: https://focusforge.onrender.com/accounts/password-reset/', text)
        self.assertNotIn('<', text)

    def test_code_is_shown_prominently(self):
        from .emailing import render_focusforge_email
        html, text = render_focusforge_email(self.user, 'S', 'Verify your email', 'Enter this code.', code='482913',
                                             code_note='Expires in 10 minutes')
        self.assertIn('letter-spacing:10px;color:#ffffff;padding-left:10px">482913</div>', html)
        self.assertIn('Your code: 482913', text)

    def test_user_text_is_escaped_in_html(self):
        from .emailing import render_focusforge_email
        html, _ = render_focusforge_email(self.user, 'S', 'H', 'Goal “<script>x</script>” is complete.')
        self.assertNotIn('<script>x', html)
