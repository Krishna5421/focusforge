import logging
from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_focusforge_email_async(user, subject, heading, message, action_url=''):
    """Queue email work on a daemon thread so web requests never wait for SMTP."""
    recipient = (user.email or '').strip()
    if not recipient:
        return False

    if action_url and action_url.startswith('/'):
        action_url = f'{settings.SITE_URL}{action_url}'
    context = {
        'name': user.first_name or user.username,
        'heading': heading,
        'message': message,
        'action_url': action_url,
        'site_name': 'FocusForge',
    }

    def deliver():
        try:
            html = render_to_string('emails/focusforge_email.html', context)
            email = EmailMultiAlternatives(subject, strip_tags(html), settings.DEFAULT_FROM_EMAIL, [recipient])
            email.attach_alternative(html, 'text/html')
            email.send(fail_silently=False)
        except Exception:
            logger.exception('FocusForge email delivery failed for user id %s', user.pk)

    Thread(target=deliver, name='focusforge-email', daemon=True).start()
    return True
