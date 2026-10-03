from django.contrib.auth import login, logout
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
from .forms import (RegisterForm, StyledLoginForm, ProfileForm, UserUpdateForm,
                    PasswordResetRequestForm, PasswordResetOTPForm, PasswordResetSetForm)
from .models import PasswordResetOTP
from . import verification
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
    return render(request, 'accounts/profile.html', {
        'profile': refresh_activity_streak(request.user),
        'weekly_consistency_score': weekly_consistency_score(request.user),
    })


@login_required
def settings_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Settings updated successfully.')
            return redirect('accounts:settings')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    return render(request, 'accounts/settings.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


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
