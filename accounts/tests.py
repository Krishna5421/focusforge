import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from tasks.models import Task
from habits.models import Habit, HabitLog
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

    def test_profile_shows_weekly_consistency_from_tasks_and_habits(self):
        today = timezone.localdate()
        Task.objects.create(user=self.user, title='Finished', due_date=timezone.now(), status='COMPLETED')
        Task.objects.create(user=self.user, title='Pending', due_date=timezone.now())
        habit = Habit.objects.create(user=self.user, name='Read', frequency='DAILY')
        HabitLog.objects.create(habit=habit, date=today, completed=True)

        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.context['weekly_consistency_score'], 67)
        self.assertContains(response, 'Weekly consistency')
        self.assertContains(response, '67%')


class AuthenticationValidationTests(TestCase):
    def test_register_shows_a_field_error_for_a_username_starting_with_underscore(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': '_not_allowed',
            'first_name': 'Krishna',
            'last_name': 'Kumar',
            'email': 'krishna@example.com',
            'password1': 'secure-password-123',
            'password2': 'secure-password-123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username cannot start with an underscore.')
        self.assertContains(response, 'has-error')


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
