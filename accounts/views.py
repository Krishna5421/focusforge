from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.db import IntegrityError, transaction
from datetime import timedelta
import logging
import secrets
from tasks.models import Task
from habits.models import Habit
from goals.models import Goal, Milestone
from .forms import (BIO_MAX_LENGTH, RegisterForm, StyledLoginForm, ProfileForm, UserUpdateForm,
                    PasswordResetRequestForm, PasswordResetOTPForm, PasswordResetSetForm)
from .models import PasswordResetOTP, PendingEmailChange
from . import deletion, email_change, verification
from .streaks import refresh_activity_streak

logger = logging.getLogger(__name__)


def weekly_consistency_score(user, today=None):
    """Return this week's completed task and scheduled-habit percentage."""
    today = today or timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    weekly_tasks = Task.objects.filter(user=user, due_date__date__range=(week_start, today))
    expected_items = weekly_tasks.count()
    completed_items = weekly_tasks.filter(status='COMPLETED').count()

    habits = Habit.objects.filter(user=user, is_active=True, created_at__date__lte=today).prefetch_related('logs')
    for habit in habits:
        first_day = max(week_start, habit.created_at.date())
        completed_dates = set(habit.logs.filter(
            date__range=(first_day, today), completed=True,
        ).values_list('date', flat=True))

        if habit.frequency == 'WEEKLY' and not habit.target_days:
            expected_items += 1
            completed_items += int(bool(completed_dates))
            continue

        target_days = habit.target_days if habit.frequency == 'WEEKLY' else range(1, 8)
        scheduled_dates = {
            first_day + timedelta(days=offset)
            for offset in range((today - first_day).days + 1)
            if (first_day + timedelta(days=offset)).isoweekday() in target_days
        }
        expected_items += len(scheduled_dates)
        completed_items += len(completed_dates & scheduled_dates)

    return round((completed_items / expected_items) * 100) if expected_items else 0


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        # Frees usernames/emails held by sign-ups that were never verified.
        verification.purge_stale_unverified()
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            try:
                with transaction.atomic():
                    user = register_form.save(commit=False)
                    user.is_active = False  # Activated once the emailed code is entered.
                    user.save()
            except IntegrityError:
                # A second, near-simultaneous registration can pass validation
                # before the first request commits. Keep this a field error.
                register_form.add_error('username', 'This username is already in use. Please choose another one.')
            else:
                return start_email_verification(request, user, 'Account created!')
    else:
        register_form = RegisterForm()

    login_form = StyledLoginForm()
    return render(request, 'accounts/auth.html', {
        'login_form': login_form,
        'register_form': register_form,
        'initial_view': 'register',
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        login_form = StyledLoginForm(request, data=request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('core:dashboard')
        else:
            pending_user = verification.find_pending_user(request.POST.get('username'), request.POST.get('password'))
            if pending_user:
                return start_email_verification(request, pending_user, 'Please verify your email first.')
            messages.error(request, 'Invalid username/email or password.')
    else:
        login_form = StyledLoginForm()

    register_form = RegisterForm()
    return render(request, 'accounts/auth.html', {
        'login_form': login_form,
        'register_form': register_form,
        'initial_view': 'login',
    })


def start_email_verification(request, user, intro):
    """Send a code (unless one was sent moments ago) and move the user to the verify page."""
    request.session[verification.SESSION_KEY] = user.pk
    if verification.resend_wait_seconds(user):
        messages.info(request, f'{intro} Use the code we already sent to {verification.mask_email(user.email)}.')
    elif verification.send_verification_code(user):
        messages.success(request, f'{intro} We sent a code to {verification.mask_email(user.email)}.')
    else:
        messages.error(request, "We couldn't send the verification email right now. Please use Resend code in a moment.")
    return redirect('accounts:verify_email')


def pending_verification_user(request):
    """The account waiting for verification in this session, or None."""
    user_id = request.session.get(verification.SESSION_KEY)
    user = User.objects.filter(pk=user_id).first() if user_id else None
    if not verification.is_pending(user):
        request.session.pop(verification.SESSION_KEY, None)
        return None
    return user


def verify_email(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    user = pending_verification_user(request)
    if user is None:
        messages.info(request, 'Your verification session has ended. Log in to get a new code.')
        return redirect('accounts:login')

    form = PasswordResetOTPForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        result, attempts_left = verification.verify_code(user, form.cleaned_data['otp'])
        if result == verification.VERIFIED:
            request.session.pop(verification.SESSION_KEY, None)
            user.refresh_from_db()
            user.skip_login_email = True  # They just got the welcome email; skip "Welcome back".
            login(request, user)
            messages.success(request, 'Email verified. Welcome to FocusForge!')
            return redirect('core:dashboard')
        if result == verification.INVALID:
            form.add_error('otp', f'That code is incorrect. {attempts_left} attempt{"s" if attempts_left != 1 else ""} left.')
        elif result == verification.EXPIRED:
            form.add_error('otp', 'This code has expired. Use Resend code to get a new one.')
        elif verification.resend_wait_seconds(user) == 0 and verification.send_verification_code(user):
            form.add_error('otp', "Too many incorrect attempts. We've emailed you a new code.")
        else:
            form.add_error('otp', 'Too many incorrect attempts. Use Resend code to get a new one.')

    return render(request, 'accounts/verify_email.html', {
        'form': form,
        'masked_email': verification.mask_email(user.email),
        'resend_wait': verification.resend_wait_seconds(user),
    })


def verify_email_resend(request):
    if request.method != 'POST':
        return redirect('accounts:verify_email')
    user = pending_verification_user(request)
    if user is None:
        messages.info(request, 'Your verification session has ended. Log in to get a new code.')
        return redirect('accounts:login')
    wait = verification.resend_wait_seconds(user)
    if wait:
        messages.info(request, f'Please wait {wait} seconds before requesting another code.')
    elif verification.send_verification_code(user):
        messages.success(request, f'A new code is on its way to {verification.mask_email(user.email)}.')
    else:
        messages.error(request, "We couldn't send the code right now. Please try again in a moment.")
    return redirect('accounts:verify_email')


def verify_email_restart(request):
    """'Wrong email?': drop the unverified sign-up so the user can register again."""
    if request.method == 'POST':
        user = pending_verification_user(request)
        if user is not None:
            user.delete()
        request.session.pop(verification.SESSION_KEY, None)
        messages.info(request, 'Sign up again with the correct email address.')
    return redirect('accounts:register')


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier']
            user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True).first()
            if user and user.email:
                code = f'{secrets.randbelow(1_000_000):06d}'
                PasswordResetOTP.objects.update_or_create(
                    user=user,
                    defaults={'code_hash': make_password(code), 'expires_at': timezone.now() + timedelta(minutes=10), 'attempts': 0},
                )
                from notifications.emailing import send_focusforge_email_async
                send_focusforge_email_async(
                    user, f'{code} is your FocusForge password reset code', 'Reset your password',
                    'Enter this code on the FocusForge password reset page to choose a new password.',
                    code=code, code_note='Expires in 10 minutes', preheader=f'Your code is {code}. It expires in 10 minutes.',
                    footer_reason='Someone asked to reset the password for this account. If it was not you, '
                                  'ignore this email; your password will stay the same.',
                )
                request.session['password_reset_user_id'] = user.pk
                messages.success(request, 'Password reset email sent successfully.')
                return redirect('accounts:password_reset_verify')
            form.add_error('identifier', 'No account was found with those details.')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'accounts/password_reset.html', {'form': form})


def password_reset_verify(request):
    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        return redirect('accounts:password_reset')
    if request.method == 'POST':
        form = PasswordResetOTPForm(request.POST)
        if form.is_valid():
            otp = PasswordResetOTP.objects.filter(user_id=user_id).first()
            if not otp or otp.is_expired():
                form.add_error('otp', 'This code has expired. Request a new one.')
            elif otp.attempts >= 5:
                form.add_error('otp', 'Too many attempts. Request a new code.')
            elif not check_password(form.cleaned_data['otp'], otp.code_hash):
                otp.attempts += 1
                otp.save(update_fields=['attempts', 'created_at'])
                form.add_error('otp', 'That code is not correct.')
            else:
                otp.delete()
                request.session['password_reset_verified_user_id'] = user_id
                request.session.pop('password_reset_user_id', None)
                return redirect('accounts:password_reset_new_password')
    else:
        form = PasswordResetOTPForm()
    return render(request, 'accounts/password_reset_verify.html', {'form': form})


def password_reset_new_password(request):
    user_id = request.session.get('password_reset_verified_user_id')
    if not user_id:
        return redirect('accounts:password_reset')
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if not user:
        request.session.pop('password_reset_verified_user_id', None)
        return redirect('accounts:password_reset')
    if request.method == 'POST':
        form = PasswordResetSetForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.save(update_fields=['password'])
            request.session.pop('password_reset_verified_user_id', None)
            messages.success(request, 'Password updated. You can now log in.')
            return redirect('accounts:login')
    else:
        form = PasswordResetSetForm()
    return render(request, 'accounts/password_reset_new_password.html', {'form': form})


@login_required
def profile_view(request):
    from django.db.models import Sum
    from achievements.models import Achievement, UserAchievement
    from pomodoro.models import PomodoroSession
    from study.models import StudySession

    user = request.user
    profile = refresh_activity_streak(user)

    def hours_and_minutes(minutes):
        hours, rest = divmod(int(minutes), 60)
        return f'{hours}h {rest}m' if hours and rest else f'{hours}h' if hours else f'{rest}m'

    focus_minutes = sum(
        (session.actual_focus_seconds or session.duration_minutes * 60) / 60
        for session in PomodoroSession.objects.filter(user=user, status='COMPLETED')
        .only('actual_focus_seconds', 'duration_minutes')
    )
    study_minutes = StudySession.objects.filter(user=user).aggregate(total=Sum('duration_minutes'))['total'] or 0
    xp_into_level = profile.total_xp % 100

    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'weekly_consistency_score': weekly_consistency_score(user),
        'xp_into_level': xp_into_level,
        'xp_to_next_level': 100 - xp_into_level,
        'next_level': profile.get_level() + 1,
        'quick_stats': [
            ('bi-check2-circle', 'Tasks done', Task.objects.filter(user=user, status='COMPLETED').count()),
            ('bi-stopwatch', 'Focus time', hours_and_minutes(focus_minutes)),
            ('bi-book', 'Study time', hours_and_minutes(study_minutes)),
            ('bi-award', 'Achievements',
             f'{UserAchievement.objects.filter(user=user).count()} / {Achievement.objects.count()}'),
        ],
    })


def render_settings(request, user_form, profile_form, password_form, delete_error=''):
    # Django autofocuses the current-password field, which would scroll the page down to it on every visit.
    password_form.fields['old_password'].widget.attrs.pop('autofocus', None)
    return render(request, 'accounts/settings.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'pending_email_change': email_change.pending_change(request.user),
        'bio_max_length': BIO_MAX_LENGTH,
        'can_delete_account': deletion.can_self_delete(request.user),
        'delete_error': delete_error,
        'delete_confirm_word': deletion.CONFIRM_WORD,
    })


@login_required
def settings_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        old_email = request.user.email or ''
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            new_email = user_form.cleaned_data['email']
            email_changed = new_email.lower() != old_email.lower()
            user = user_form.save(commit=False)
            if email_changed:
                user.email = old_email  # The new address is applied only after its code is confirmed.
            user.save()
            profile_form.save()
            if email_changed:
                if email_change.request_email_change(user, new_email):
                    messages.success(request, f'Profile saved. Enter the code we sent to {verification.mask_email(new_email)} to switch your email.')
                else:
                    messages.error(request, "Profile saved, but we couldn't send the code to your new email. Use Resend code in a moment.")
                return redirect('accounts:confirm_email_change')
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        # Show the address that is actually saved, not the rejected one, elsewhere on the page.
        request.user.email = old_email
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    return render_settings(request, user_form, profile_form, PasswordChangeForm(request.user))


@login_required
def change_password(request):
    if request.method != 'POST':
        return redirect('accounts:settings')
    password_form = PasswordChangeForm(request.user, request.POST)
    if password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)  # Stay signed in on this device.
        messages.success(request, 'Password changed successfully.')
        return redirect('accounts:settings')
    messages.error(request, 'Your password was not changed. Please fix the errors below.')
    return render_settings(request, UserUpdateForm(instance=request.user),
                           ProfileForm(instance=request.user.profile), password_form)


@login_required
def delete_account(request):
    if request.method != 'POST':
        return redirect('accounts:settings')
    user = request.user

    def show_error(message):
        return render_settings(request, UserUpdateForm(instance=user), ProfileForm(instance=user.profile),
                               PasswordChangeForm(user), delete_error=message)

    if not deletion.can_self_delete(user):
        # Admins don't get the danger-zone dialog, so report this as a page message instead.
        messages.error(request, 'Admin accounts cannot be deleted from here. Ask another admin to remove this account.')
        return redirect('accounts:settings')
    if request.POST.get('confirm', '').strip() != deletion.CONFIRM_WORD:
        return show_error(f'Type {deletion.CONFIRM_WORD} in capital letters to confirm.')
    if not user.check_password(request.POST.get('password', '')):
        return show_error('Incorrect password. Your account was not deleted.')

    try:
        deletion.delete_account(user)
    except Exception:
        logger.exception('Account deletion failed for user %s', user.pk)
        return show_error('We could not delete your account right now. Nothing was removed. Please try again.')
    logout(request)
    messages.success(request, 'Your account has been deleted.')
    return redirect('accounts:login')


@login_required
def remove_profile_photo(request):
    if request.method == 'POST':
        profile = request.user.profile
        if profile.profile_picture:
            try:
                profile.profile_picture.delete(save=False)
            except Exception:
                # The stored file may already be gone; the profile should still drop the reference.
                logger.exception('Could not delete profile picture file for user %s', request.user.pk)
            profile.profile_picture = None
            profile.save(update_fields=['profile_picture'])
            messages.success(request, 'Profile photo removed.')
    return redirect('accounts:settings')


@login_required
def confirm_email_change(request):
    change = email_change.pending_change(request.user)
    if change is None:
        messages.info(request, 'There is no email change waiting for confirmation.')
        return redirect('accounts:settings')

    form = PasswordResetOTPForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        result, attempts_left = email_change.confirm_email_change(request.user, form.cleaned_data['otp'])
        if result == verification.VERIFIED:
            messages.success(request, 'Your email address has been updated.')
            return redirect('accounts:profile')
        if result == email_change.TAKEN:
            messages.error(request, 'That email is now used by another account. Choose a different one.')
            return redirect('accounts:settings')
        if result == verification.INVALID:
            form.add_error('otp', f'That code is incorrect. {attempts_left} attempt{"s" if attempts_left != 1 else ""} left.')
        elif result == verification.EXPIRED:
            form.add_error('otp', 'This code has expired. Use Resend code to get a new one.')
        else:
            form.add_error('otp', 'Too many incorrect attempts. Use Resend code to get a new one.')

    return render(request, 'accounts/confirm_email_change.html', {
        'form': form,
        'masked_email': verification.mask_email(change.new_email),
        'resend_wait': email_change.resend_wait_seconds(change),
    })


@login_required
def confirm_email_change_resend(request):
    if request.method == 'POST':
        change = email_change.pending_change(request.user)
        if change is None:
            return redirect('accounts:settings')
        wait = email_change.resend_wait_seconds(change)
        if wait:
            messages.info(request, f'Please wait {wait} seconds before requesting another code.')
        elif email_change.resend_code(request.user):
            messages.success(request, f'A new code is on its way to {verification.mask_email(change.new_email)}.')
        else:
            messages.error(request, "We couldn't send the code right now. Please try again in a moment.")
    return redirect('accounts:confirm_email_change')


@login_required
def cancel_email_change(request):
    if request.method == 'POST':
        PendingEmailChange.objects.filter(user=request.user).delete()
        messages.info(request, 'Email change cancelled. Your email address is unchanged.')
    return redirect('accounts:settings')


@login_required
def export_data(request):
    from .reports import build_productivity_report

    period = request.GET.get('period', 'weekly')
    if period not in ('weekly', 'monthly'):
        period = 'weekly'
    try:
        pdf = build_productivity_report(request.user, period)
    except Exception:
        logger.exception('PDF report export failed for user %s', request.user.pk)
        messages.error(request, 'We could not generate your report right now. Please try again in a moment.')
        return redirect('accounts:profile')
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="focusforge-{period}-report.pdf"'
    return response
