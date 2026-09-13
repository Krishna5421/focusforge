import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from tasks.models import Task
from .models import PasswordResetOTP


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='profile-user', password='password', email='old@example.com')
        self.other = User.objects.create_user(username='other-user', password='password')
        self.client.login(username='profile-user', password='password')

    def test_profile_edit_updates_user_and_bio(self):
        response = self.client.post(reverse('accounts:settings'), {
            'first_name': 'Krishna', 'last_name': 'Kumar', 'username': 'krishna',
            'email': 'krishna@example.com', 'bio': 'Building better routines.',
        })

        self.assertRedirects(response, reverse('accounts:settings'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'krishna')
        self.assertEqual(self.user.first_name, 'Krishna')
        self.assertEqual(self.user.profile.bio, 'Building better routines.')

    def test_export_contains_only_current_users_data(self):
        Task.objects.create(user=self.user, title='My task')
        Task.objects.create(user=self.other, title='Other task')

        response = self.client.get(reverse('accounts:export_data'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment;', response['Content-Disposition'])
        data = json.loads(response.content)
        self.assertEqual(data['profile']['username'], 'profile-user')
        self.assertEqual([task['title'] for task in data['tasks']], ['My task'])


class PasswordResetOTPTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reset-user', email='reset@example.com', password='old-password')

    @patch('notifications.emailing.send_focusforge_email_async')
    def test_username_request_and_otp_can_reset_password(self, send_email):
        response = self.client.post(reverse('accounts:password_reset'), {'identifier': 'reset-user'})
        self.assertRedirects(response, reverse('accounts:password_reset_verify'))
        self.assertTrue(PasswordResetOTP.objects.filter(user=self.user).exists())
        send_email.assert_called_once()

        PasswordResetOTP.objects.filter(user=self.user).update(code_hash=make_password('123456'))
        response = self.client.post(reverse('accounts:password_reset_verify'), {'otp': '123456'})
        self.assertRedirects(response, reverse('accounts:password_reset_new_password'))
        response = self.client.post(reverse('accounts:password_reset_new_password'), {
            'new_password1': 'new-secure-password', 'new_password2': 'new-secure-password',
        })
        self.assertRedirects(response, reverse('accounts:login'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-secure-password'))

    def test_expired_otp_is_rejected(self):
        PasswordResetOTP.objects.create(user=self.user, code_hash=make_password('123456'),
                                        expires_at=timezone.now() - timedelta(minutes=1))
        session = self.client.session
        session['password_reset_user_id'] = self.user.pk
        session.save()
        response = self.client.post(reverse('accounts:password_reset_verify'), {'otp': '123456'})
        self.assertContains(response, 'This code has expired.')
