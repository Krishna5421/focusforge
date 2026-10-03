"""Email verification for new sign-ups.

A new account is created inactive and receives a 6-digit code by email. Entering the
code activates it. Accounts that are never verified are removed after a day so the
email address (or username) can be registered by its real owner.
"""
import logging
import secrets
import sys
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import EmailVerificationOTP, Profile

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)
UNVERIFIED_ACCOUNT_TTL = timedelta(hours=24)
SESSION_KEY = 'email_verification_user_id'

# verify_code() results
VERIFIED, INVALID, EXPIRED, LOCKED, MISSING = 'verified', 'invalid', 'expired', 'locked', 'missing'


def is_pending(user):
    """True for an account that signed up but has not confirmed its email yet."""
    # Only sign-ups still holding a code count; admin-deactivated accounts never qualify.
    if user is None or user.is_active or not EmailVerificationOTP.objects.filter(user=user).exists():
        return False
    profile = Profile.objects.filter(user=user).first()
    return profile is None or not profile.email_verified


def mask_email(email):
    name, _, domain = (email or '').partition('@')
    if not domain:
        return email
    visible = name[:2] if len(name) > 2 else name[:1]
    return f'{visible}{"*" * max(3, len(name) - len(visible))}@{domain}'


def resend_wait_seconds(user):
    otp = EmailVerificationOTP.objects.filter(user=user).first()
    if otp is None:
        return 0
    remaining = (otp.sent_at + RESEND_COOLDOWN - timezone.now()).total_seconds()
    return max(0, int(remaining + 0.999))


def deliver_code_email(user, code):
    """Send the code and wait for the result, so the user can be told if it failed."""
    if 'test' in sys.argv:
        # Tests must never send real email; they patch this function to simulate failures.
        return True
    from notifications.emailing import render_focusforge_email, send_brevo_email
    try:
        subject = f'{code} is your FocusForge verification code'
        html, text = render_focusforge_email(
            user, subject, 'Verify your email', 'Enter this code on the FocusForge sign-up page to finish creating your account.',
            code=code, code_note='Expires in 10 minutes', preheader=f'Your code is {code}. It expires in 10 minutes.',
            footer_reason=f'Someone signed up for FocusForge with {user.email}. If it was not you, you can ignore this email.',
        )
        return send_brevo_email(user.email, subject, html, text)
    except Exception:
        logger.exception('Verification email failed for user %s', user.pk)
        return False


def send_verification_code(user):
    """Create a fresh code and email it. Returns True if the email was accepted for delivery."""
    code = f'{secrets.randbelow(1_000_000):06d}'
    now = timezone.now()
    EmailVerificationOTP.objects.update_or_create(user=user, defaults={
        'code_hash': make_password(code), 'expires_at': now + CODE_TTL, 'attempts': 0, 'sent_at': now,
    })
    sent = deliver_code_email(user, code)
    if not sent:
        logger.warning('Could not send verification code to user %s', user.pk)
        # Nothing reached the user, so let them retry straight away instead of waiting out the cooldown.
        EmailVerificationOTP.objects.filter(user=user).update(sent_at=now - RESEND_COOLDOWN)
    return sent


def verify_code(user, code):
    """Check a submitted code. Returns (result, attempts_left)."""
    with transaction.atomic():
        otp = EmailVerificationOTP.objects.select_for_update().filter(user=user).first()
        if otp is None:
            return MISSING, 0
        if otp.attempts >= MAX_ATTEMPTS:
            return LOCKED, 0
        if otp.is_expired():
            return EXPIRED, 0
        if not check_password(code, otp.code_hash):
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            left = MAX_ATTEMPTS - otp.attempts
            return (LOCKED, 0) if left <= 0 else (INVALID, left)
        otp.delete()
    activate(user)
    return VERIFIED, MAX_ATTEMPTS


def activate(user):
    user.is_active = True
    user.save(update_fields=['is_active'])
    Profile.objects.update_or_create(user=user, defaults={'email_verified': True})
    send_welcome_email(user)


def send_welcome_email(user):
    from notifications.emailing import send_focusforge_email_async
    send_focusforge_email_async(
        user, 'Welcome to FocusForge', 'Welcome to FocusForge!',
        'Your account is ready. Here is a simple way to make today count:', '/', action_label='Open your dashboard',
        preheader='Your account is ready. Three small steps to get started.',
        steps=[
            {'title': 'Add your first task', 'text': 'Pick one thing you want done today and give it a due time.', 'url': '/tasks/'},
            {'title': 'Start one daily habit', 'text': 'Keep it small, like reading 10 pages, and build a streak.', 'url': '/habits/'},
            {'title': 'Try a 25-minute focus session', 'text': 'Use the Pomodoro timer to work without distractions.', 'url': '/pomodoro/'},
        ],
    )


def find_pending_user(identifier, password):
    """The unverified account matching these login details, if the password is right."""
    identifier = (identifier or '').strip()
    if not identifier or not password:
        return None
    candidates = User.objects.filter(Q(username=identifier) | Q(email__iexact=identifier), is_active=False)
    for user in candidates[:2]:
        if user.check_password(password) and is_pending(user):
            return user
    return None


def purge_stale_unverified(now=None):
    """Delete sign-ups that were never verified within UNVERIFIED_ACCOUNT_TTL."""
    cutoff = (now or timezone.now()) - UNVERIFIED_ACCOUNT_TTL
    stale = User.objects.filter(is_active=False, date_joined__lt=cutoff, profile__email_verified=False,
                                email_verification_otp__isnull=False)
    deleted, _ = stale.delete()
    return deleted
