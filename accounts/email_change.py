"""Changing the account email: the new address must confirm a code before it replaces the old one."""
import logging
import secrets
import sys

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import PendingEmailChange, Profile
from .verification import CODE_TTL, EXPIRED, INVALID, LOCKED, MAX_ATTEMPTS, MISSING, RESEND_COOLDOWN, VERIFIED

logger = logging.getLogger(__name__)

TAKEN = 'taken'  # Someone else registered the address while the change was pending.


def pending_change(user):
    return PendingEmailChange.objects.filter(user=user).first()


def resend_wait_seconds(change):
    if change is None:
        return 0
    remaining = (change.sent_at + RESEND_COOLDOWN - timezone.now()).total_seconds()
    return max(0, int(remaining + 0.999))


def deliver_change_code(user, new_email, code):
    """Email the code to the NEW address and wait for the result."""
    if 'test' in sys.argv:
        return True  # Tests patch this to simulate failures; never send real email.
    from notifications.emailing import render_focusforge_email, send_brevo_email
    try:
        subject = f'{code} is your FocusForge email change code'
        # Rendered for the new address: the footer must not mention the old one.
        recipient = User(username=user.username, first_name=user.first_name, email=new_email, is_active=True)
        html, text = render_focusforge_email(
            recipient, subject, 'Confirm your new email',
            'Enter this code in FocusForge to use this address for your account.',
            code=code, code_note='Expires in 10 minutes', preheader=f'Your code is {code}. It expires in 10 minutes.',
            footer_reason=f'Someone asked to use {new_email} for a FocusForge account. If it was not you, ignore this email.',
        )
        return send_brevo_email(new_email, subject, html, text)
    except Exception:
        logger.exception('Email change code failed for user %s', user.pk)
        return False


def request_email_change(user, new_email):
    """Store the pending address and send it a code. Returns True if the email was sent."""
    code = f'{secrets.randbelow(1_000_000):06d}'
    now = timezone.now()
    PendingEmailChange.objects.update_or_create(user=user, defaults={
        'new_email': new_email, 'code_hash': make_password(code), 'expires_at': now + CODE_TTL,
        'attempts': 0, 'sent_at': now,
    })
    sent = deliver_change_code(user, new_email, code)
    if not sent:
        # Nothing arrived, so allow an immediate resend.
        PendingEmailChange.objects.filter(user=user).update(sent_at=now - RESEND_COOLDOWN)
    return sent


def resend_code(user):
    change = pending_change(user)
    return request_email_change(user, change.new_email) if change else False


def confirm_email_change(user, code):
    """Apply the pending email if the code is right. Returns (result, attempts_left)."""
    with transaction.atomic():
        change = PendingEmailChange.objects.select_for_update().filter(user=user).first()
        if change is None:
            return MISSING, 0
        if change.attempts >= MAX_ATTEMPTS:
            return LOCKED, 0
        if change.is_expired():
            return EXPIRED, 0
        if not check_password(code, change.code_hash):
            change.attempts += 1
            change.save(update_fields=['attempts'])
            left = MAX_ATTEMPTS - change.attempts
            return (LOCKED, 0) if left <= 0 else (INVALID, left)
        if User.objects.exclude(pk=user.pk).filter(email__iexact=change.new_email).exists():
            change.delete()
            return TAKEN, 0
        old_email = user.email
        user.email = change.new_email
        user.save(update_fields=['email'])
        Profile.objects.update_or_create(user=user, defaults={'email_verified': True})
        change.delete()
    notify_old_address(user, old_email)
    return VERIFIED, MAX_ATTEMPTS


def notify_old_address(user, old_email):
    """Tell the previous address about the change, in case it was not the owner."""
    if not old_email or old_email.lower() == user.email.lower():
        return
    from notifications.emailing import send_focusforge_email_async
    previous = User(pk=user.pk, username=user.username, first_name=user.first_name, email=old_email, is_active=True)
    send_focusforge_email_async(
        previous, 'Your FocusForge email was changed', 'Your email address was changed',
        f'Your FocusForge account now uses a new email address. If you did not make this change, '
        f'reset your password right away.', '/accounts/password-reset/', action_label='Reset your password',
        preheader='The email address on your FocusForge account was changed.',
    )
