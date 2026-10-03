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
            'first_name': 'Krishna', 'last_name': 'Yadav', 'username': 'krishna',
            'email': 'old@example.com', 'bio': 'Building better routines.',
        })

        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'krishna')
        self.assertEqual(self.user.first_name, 'Krishna')
        self.assertEqual(self.user.profile.bio, 'Building better routines.')

    def test_export_creates_a_pdf_report(self):
        Task.objects.create(user=self.user, title='My task')
        Task.objects.create(user=self.other, title='Other task')

        response = self.client.get(f'{reverse("accounts:export_data")}?period=weekly')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('focusforge-weekly-report.pdf', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_export_monthly_report_with_activity(self):
        Task.objects.create(user=self.user, title='Done <b>&</b> dusted', status='COMPLETED', completed_at=timezone.now())
        habit = Habit.objects.create(user=self.user, name='Read', frequency='WEEKLY', target_days=[1, 3, 5])
        HabitLog.objects.create(habit=habit, date=timezone.localdate(), completed=True)

        response = self.client.get(f'{reverse("accounts:export_data")}?period=monthly')

        self.assertEqual(response.status_code, 200)
        self.assertIn('focusforge-monthly-report.pdf', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_export_unknown_period_falls_back_to_weekly(self):
        response = self.client.get(f'{reverse("accounts:export_data")}?period=yearly')
        self.assertIn('focusforge-weekly-report.pdf', response['Content-Disposition'])

    def test_export_failure_redirects_with_message(self):
        with patch('accounts.reports.build_productivity_report', side_effect=RuntimeError('boom')), \
                self.assertLogs('accounts.views', level='ERROR'):
            response = self.client.get(reverse('accounts:export_data'), follow=True)

        self.assertRedirects(response, reverse('accounts:profile'))
        self.assertContains(response, 'could not generate your report')

    def test_report_period_bounds_and_deltas(self):
        from datetime import date
        from .reports import delta_note, period_bounds

        start, end, previous_start, previous_end, label, compare = period_bounds('monthly', date(2026, 3, 31))
        self.assertEqual((start, end), (date(2026, 3, 1), date(2026, 3, 31)))
        self.assertEqual((previous_start, previous_end), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual((label, compare), ('March 2026', 'last month'))

        start, end, previous_start, previous_end, _, _ = period_bounds('weekly', date(2026, 10, 2))
        self.assertEqual((start, end), (date(2026, 9, 28), date(2026, 10, 4)))
        self.assertEqual((previous_start, previous_end), (date(2026, 9, 21), date(2026, 9, 25)))

        self.assertEqual(delta_note(0, 0, 'last week')[0], 'No activity yet')
        self.assertEqual(delta_note(5, 3, 'last week')[0], '+2 vs last week')
        self.assertEqual(delta_note(30, 90, 'last week', minutes=True)[0], '-1h vs last week')

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
            'last_name': 'Yadav',
            'email': 'krishna@example.com',
            'password1': 'secure-password-123',
            'password2': 'secure-password-123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username cannot start with an underscore.')
        self.assertContains(response, 'has-error')

    def test_duplicate_registration_stays_on_the_form_with_a_username_error(self):
        User.objects.create_user(username='already-used', password='password')

        response = self.client.post(reverse('accounts:register'), {
            'username': 'already-used',
            'first_name': 'Krishna',
            'last_name': 'Yadav',
            'email': 'krishna@example.com',
            'password1': 'secure-password-123',
            'password2': 'secure-password-123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This username is already in use.')

    def test_duplicate_email_registration_shows_email_field_error(self):
        User.objects.create_user(username='first-account', password='password', email='same@example.com')

        response = self.client.post(reverse('accounts:register'), {
            'username': 'different-account',
            'first_name': 'Krishna',
            'last_name': 'Yadav',
            'email': 'SAME@example.com',
            'password1': 'secure-password-123',
            'password2': 'secure-password-123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This email is already registered. Please use a different email or log in.')
        self.assertEqual(User.objects.filter(email__iexact='same@example.com').count(), 1)


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

    def test_unknown_password_reset_identifier_shows_clear_error(self):
        response = self.client.post(reverse('accounts:password_reset'), {'identifier': 'missing-account'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No account was found with those details.')


class UsernameOrEmailLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='riya', email='Riya@Example.com', password='S3cure-pass!')

    def login(self, identifier, password='S3cure-pass!'):
        return self.client.post(reverse('accounts:login'), {'username': identifier, 'password': password})

    def test_login_with_username(self):
        self.assertRedirects(self.login('riya'), reverse('core:dashboard'), fetch_redirect_response=False)

    def test_login_with_email_any_case(self):
        self.assertRedirects(self.login('  riya@example.COM '), reverse('core:dashboard'), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_wrong_password_or_unknown_account_fails(self):
        for identifier, password in (('riya@example.com', 'wrong'), ('nobody@example.com', 'S3cure-pass!'), ('nobody', 'x')):
            response = self.login(identifier, password)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Incorrect username/email or password')

    def test_inactive_user_cannot_log_in_with_email(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.login('riya@example.com')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_duplicate_email_is_refused_instead_of_guessing(self):
        User.objects.create_user(username='riya2', email='riya@example.com', password='S3cure-pass!')
        self.login('riya@example.com')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.login('riya2'), reverse('core:dashboard'), fetch_redirect_response=False)

    def test_api_token_login_accepts_email(self):
        response = self.client.post('/api/auth/login/', {'username': 'riya@example.com', 'password': 'S3cure-pass!'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())


class EmailVerificationTests(TestCase):
    REGISTER = {
        'username': 'newbie', 'first_name': 'New', 'last_name': 'User', 'email': 'newbie@example.com',
        'password1': 'Str0ng-pass-123', 'password2': 'Str0ng-pass-123',
    }

    def register(self, code='123456', sent=True):
        """Sign up while capturing the emailed code (no real email is sent)."""
        self.codes = []

        def fake_deliver(user, code_sent):
            self.codes.append(code_sent)
            return sent
        with patch('accounts.verification.deliver_code_email', side_effect=fake_deliver):
            return self.client.post(reverse('accounts:register'), self.REGISTER)

    def user(self):
        return User.objects.get(username='newbie')

    def test_signup_creates_inactive_account_and_opens_verify_page(self):
        response = self.register()

        self.assertRedirects(response, reverse('accounts:verify_email'))
        self.assertFalse(self.user().is_active)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(self.codes), 1)
        page = self.client.get(reverse('accounts:verify_email'))
        self.assertContains(page, 'ne****@example.com')

    def test_correct_code_activates_and_logs_in(self):
        self.register()
        response = self.client.post(reverse('accounts:verify_email'), {'otp': self.codes[0]})

        self.assertRedirects(response, reverse('core:dashboard'), fetch_redirect_response=False)
        user = self.user()
        self.assertTrue(user.is_active)
        self.assertTrue(user.profile.email_verified)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_new_account_gets_welcome_email_not_welcome_back(self):
        self.register()
        with patch('notifications.emailing.send_focusforge_email_async') as send:
            self.client.post(reverse('accounts:verify_email'), {'otp': self.codes[0]})
        self.assertEqual([call.args[1] for call in send.call_args_list], ['Welcome to FocusForge'])

        self.client.logout()
        with patch('notifications.emailing.send_focusforge_email_async') as send:
            self.client.post(reverse('accounts:login'), {'username': 'newbie', 'password': 'Str0ng-pass-123'})
        self.assertEqual([call.args[1] for call in send.call_args_list], ['FocusForge · Welcome back'])

    def test_wrong_code_counts_down_then_locks_and_resends(self):
        self.register()
        wrong = '000000' if self.codes[0] != '000000' else '111111'
        response = self.client.post(reverse('accounts:verify_email'), {'otp': wrong})
        self.assertContains(response, '4 attempts left')

        from accounts.models import EmailVerificationOTP
        EmailVerificationOTP.objects.filter(user=self.user()).update(attempts=5, sent_at=timezone.now() - timedelta(minutes=5))
        with patch('accounts.verification.deliver_code_email', return_value=True) as deliver:
            response = self.client.post(reverse('accounts:verify_email'), {'otp': self.codes[0]})
        self.assertContains(response, 'emailed you a new code')
        deliver.assert_called_once()
        self.assertFalse(self.user().is_active)

    def test_expired_code_is_rejected(self):
        self.register()
        from accounts.models import EmailVerificationOTP
        EmailVerificationOTP.objects.filter(user=self.user()).update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.client.post(reverse('accounts:verify_email'), {'otp': self.codes[0]})
        self.assertContains(response, 'This code has expired')
        self.assertFalse(self.user().is_active)

    def test_email_failure_shows_message_and_allows_immediate_resend(self):
        response = self.register(sent=False)
        page = self.client.get(response.url)
        self.assertContains(page, 'couldn&#x27;t send the verification email')
        self.assertContains(page, 'data-countdown="0"')

    def test_resend_respects_cooldown(self):
        self.register()
        with patch('accounts.verification.deliver_code_email', return_value=True) as deliver:
            response = self.client.post(reverse('accounts:verify_email_resend'), follow=True)
        self.assertContains(response, 'Please wait')
        deliver.assert_not_called()

    def test_login_before_verifying_sends_user_to_verify_page(self):
        self.register()
        self.client.session.flush()
        from accounts.models import EmailVerificationOTP
        EmailVerificationOTP.objects.filter(user=self.user()).update(sent_at=timezone.now() - timedelta(minutes=5))
        with patch('accounts.verification.deliver_code_email', return_value=True) as deliver:
            response = self.client.post(reverse('accounts:login'), {'username': 'newbie@example.com', 'password': 'Str0ng-pass-123'})
        self.assertRedirects(response, reverse('accounts:verify_email'))
        deliver.assert_called_once()

    def test_wrong_password_for_unverified_account_gives_normal_error(self):
        self.register()
        response = self.client.post(reverse('accounts:login'), {'username': 'newbie', 'password': 'nope'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect username/email or password')

    def test_wrong_email_restart_deletes_pending_signup(self):
        self.register()
        response = self.client.post(reverse('accounts:verify_email_restart'))
        self.assertRedirects(response, reverse('accounts:register'), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_verify_page_without_session_redirects_to_login(self):
        response = self.client.get(reverse('accounts:verify_email'))
        self.assertRedirects(response, reverse('accounts:login'), fetch_redirect_response=False)

    def test_stale_unverified_signup_frees_email_but_others_are_kept(self):
        self.register()
        User.objects.filter(username='newbie').update(date_joined=timezone.now() - timedelta(days=2))
        deactivated = User.objects.create_user('old-admin-made', email='x@example.com', password='x', is_active=False)
        self.client.session.flush()

        response = self.register()
        self.assertRedirects(response, reverse('accounts:verify_email'))
        self.assertEqual(User.objects.filter(email__iexact='newbie@example.com').count(), 1)
        self.assertTrue(User.objects.filter(pk=deactivated.pk).exists())

    def test_admin_deactivated_account_cannot_verify_itself(self):
        User.objects.create_user('blocked', email='blocked@example.com', password='Str0ng-pass-123', is_active=False)
        response = self.client.post(reverse('accounts:login'), {'username': 'blocked', 'password': 'Str0ng-pass-123'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('email_verification_user_id', self.client.session)

    def test_api_signup_requires_verification(self):
        codes = []
        with patch('accounts.verification.deliver_code_email', side_effect=lambda user, code: codes.append(code) or True):
            response = self.client.post('/api/auth/register/', {
                'username': 'apiuser', 'email': 'api@example.com', 'password': 'Str0ng-pass-123',
            }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['verification_required'])
        login = self.client.post('/api/auth/login/', {'username': 'apiuser', 'password': 'Str0ng-pass-123'}, content_type='application/json')
        self.assertEqual(login.status_code, 401)

        verify = self.client.post('/api/auth/verify-email/', {'email': 'api@example.com', 'code': codes[0]},
                                  content_type='application/json')
        self.assertEqual(verify.status_code, 200)
        login = self.client.post('/api/auth/login/', {'username': 'apiuser', 'password': 'Str0ng-pass-123'}, content_type='application/json')
        self.assertEqual(login.status_code, 200)

    def test_api_signup_requires_email(self):
        response = self.client.post('/api/auth/register/', {'username': 'noemail', 'password': 'Str0ng-pass-123'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json())


class ActivityStreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('streaker', password='pass12345')
        self.client.login(username='streaker', password='pass12345')
        self.today = timezone.localdate()

    def days_ago(self, n):
        return self.today - timedelta(days=n)

    def test_calculation_matches_the_weekly_example(self):
        from datetime import date
        from .streaks import calculate_streaks
        mon, tue, wed, thu, fri = (date(2026, 9, 28) + timedelta(days=i) for i in range(5))
        self.assertEqual(calculate_streaks({mon, tue}, wed), (2, 2))          # Wed, nothing yet: still 2
        self.assertEqual(calculate_streaks({mon, tue, wed}, wed), (3, 3))     # study session on Wed
        self.assertEqual(calculate_streaks({mon, tue, wed}, fri), (0, 3))     # Thu missed
        self.assertEqual(calculate_streaks({mon, tue, wed, fri}, fri), (1, 3))
        self.assertEqual(calculate_streaks(set(), fri), (0, 0))

    def test_every_activity_type_counts(self):
        from habits.models import Habit, HabitLog
        from pomodoro.models import PomodoroSession
        from study.models import StudySession, Subject
        from .streaks import refresh_activity_streak
        now = timezone.now()
        Task.objects.create(user=self.user, title='Done', status='COMPLETED', completed_at=now)
        habit = Habit.objects.create(user=self.user, name='Read')
        HabitLog.objects.create(habit=habit, date=self.days_ago(1), completed=True)
        PomodoroSession.objects.create(user=self.user, status='COMPLETED', duration_minutes=25,
                                       actual_focus_seconds=1500, completed_at=now - timedelta(days=2))
        StudySession.objects.create(user=self.user, subject=Subject.objects.create(user=self.user, name='OS'),
                                    date=self.days_ago(3), duration_minutes=30)
        # Day 4 has only a pending task and an incomplete habit log, which must not count.
        Task.objects.create(user=self.user, title='Pending', due_date=now - timedelta(days=4))
        HabitLog.objects.create(habit=habit, date=self.days_ago(4), completed=False)

        profile = refresh_activity_streak(self.user)
        self.assertEqual((profile.current_streak, profile.longest_streak), (4, 4))

    def test_unchecking_the_only_activity_lowers_the_streak(self):
        from .streaks import refresh_activity_streak
        Task.objects.create(user=self.user, title='Yesterday', status='COMPLETED', completed_at=timezone.now() - timedelta(days=1))
        task = Task.objects.create(user=self.user, title='Today', status='COMPLETED', completed_at=timezone.now())
        self.assertEqual(refresh_activity_streak(self.user).current_streak, 2)

        self.client.post(reverse('tasks:ajax_toggle_status', args=[task.pk]))
        # Today undone: the streak falls back to the run that ended yesterday.
        self.assertEqual(refresh_activity_streak(self.user).current_streak, 1)

    def test_dashboard_profile_and_api_show_the_streak(self):
        Task.objects.create(user=self.user, title='Done', status='COMPLETED', completed_at=timezone.now())
        self.assertContains(self.client.get(reverse('core:dashboard')), 'data-streak-current>1d')
        self.assertEqual(self.client.get(reverse('accounts:profile')).context['profile'].current_streak, 1)
        self.assertEqual(self.client.get('/api/dashboard-summary/').json()['current_streak'], 1)

    def test_profile_api_cannot_change_xp_or_streaks(self):
        response = self.client.patch('/api/auth/profile/', {'total_xp': 99999, 'current_streak': 365, 'bio': 'Hi'},
                                     content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.total_xp, 0)
        self.assertEqual(self.user.profile.current_streak, 0)
        self.assertEqual(self.user.profile.bio, 'Hi')


class EditProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='editor', email='old@example.com', password='Old-pass-123',
                                             first_name='Ed')
        self.client.login(username='editor', password='Old-pass-123')

    def form_data(self, **changes):
        data = {'first_name': 'Ed', 'last_name': '', 'username': 'editor', 'email': 'old@example.com', 'bio': ''}
        data.update(changes)
        return data

    def change_email(self, new_email='new@example.com', sent=True):
        self.codes = []

        def fake_deliver(user, address, code):
            self.codes.append(code)
            return sent
        with patch('accounts.email_change.deliver_change_code', side_effect=fake_deliver):
            return self.client.post(reverse('accounts:settings'), self.form_data(email=new_email, first_name='Eddie'))

    def test_email_change_waits_for_code_but_other_fields_save(self):
        response = self.change_email()

        self.assertRedirects(response, reverse('accounts:confirm_email_change'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')
        self.assertEqual(self.user.first_name, 'Eddie')
        self.assertContains(self.client.get(reverse('accounts:settings')), 'Email change pending')

    def test_correct_code_switches_email_and_notifies_old_address(self):
        self.change_email()
        with patch('notifications.emailing.send_focusforge_email_async') as notify:
            response = self.client.post(reverse('accounts:confirm_email_change'), {'otp': self.codes[0]})

        self.assertRedirects(response, reverse('accounts:profile'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertEqual(notify.call_args.args[0].email, 'old@example.com')

    def test_wrong_code_keeps_old_email(self):
        self.change_email()
        wrong = '000000' if self.codes[0] != '000000' else '111111'
        response = self.client.post(reverse('accounts:confirm_email_change'), {'otp': wrong})
        self.assertContains(response, '4 attempts left')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')

    def test_address_taken_while_pending_is_rejected(self):
        self.change_email()
        User.objects.create_user('other', email='NEW@example.com', password='x')
        response = self.client.post(reverse('accounts:confirm_email_change'), {'otp': self.codes[0]}, follow=True)
        self.assertContains(response, 'now used by another account')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')

    def test_cancel_and_send_failure(self):
        response = self.change_email(sent=False)
        page = self.client.get(response.url)
        self.assertContains(page, 'data-countdown="0"')
        self.client.post(reverse('accounts:cancel_email_change'))
        self.assertRedirects(self.client.get(reverse('accounts:confirm_email_change')), reverse('accounts:settings'))

    def test_email_cannot_be_blank(self):
        response = self.client.post(reverse('accounts:settings'), self.form_data(email=''))
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')

    def test_change_password_keeps_session(self):
        response = self.client.post(reverse('accounts:change_password'), {
            'old_password': 'Old-pass-123', 'new_password1': 'Brand-new-pass-456', 'new_password2': 'Brand-new-pass-456',
        })
        self.assertRedirects(response, reverse('accounts:settings'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Brand-new-pass-456'))
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 200)

    def test_change_password_wrong_current_password(self):
        response = self.client.post(reverse('accounts:change_password'), {
            'old_password': 'nope', 'new_password1': 'Brand-new-pass-456', 'new_password2': 'Brand-new-pass-456',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your old password was entered incorrectly')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Old-pass-123'))

    def test_remove_photo(self):
        from accounts.models import Profile
        Profile.objects.filter(user=self.user).update(profile_picture='profiles/me.png')
        with patch('django.db.models.fields.files.FieldFile.delete') as delete_file:
            response = self.client.post(reverse('accounts:remove_profile_photo'))
        self.assertRedirects(response, reverse('accounts:settings'), fetch_redirect_response=False)
        delete_file.assert_called_once()
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.profile_picture)

    def test_large_or_wrong_type_photo_is_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        big = SimpleUploadedFile('big.png', b'x' * (2 * 1024 * 1024 + 1), content_type='image/png')
        response = self.client.post(reverse('accounts:settings'), {**self.form_data(), 'profile_picture': big})
        self.assertContains(response, 'larger than 2 MB')
        gif = SimpleUploadedFile('a.gif', b'GIF89a', content_type='image/gif')
        response = self.client.post(reverse('accounts:settings'), {**self.form_data(), 'profile_picture': gif})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.user.profile.profile_picture)

    def test_bio_limit(self):
        response = self.client.post(reverse('accounts:settings'), self.form_data(bio='x' * 201))
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, '')
