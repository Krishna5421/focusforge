import logging
import sys
from threading import Thread

import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

BREVO_TRANSACTIONAL_EMAIL_URL = 'https://api.brevo.com/v3/smtp/email'


def send_brevo_email(recipient, subject, html_content, text_content):
    """Send one transactional email through Brevo and return whether it succeeded."""
    if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_EMAIL:
        logger.error('Brevo email delivery is not configured.')
        return False

    payload = {
        'sender': {
            'email': settings.BREVO_SENDER_EMAIL,
            'name': settings.BREVO_SENDER_NAME,
        },
        'to': [{'email': recipient}],
        'subject': subject,
        'htmlContent': html_content,
        'textContent': text_content,
    }
    headers = {
        'accept': 'application/json',
        'api-key': settings.BREVO_API_KEY,
        'content-type': 'application/json',
    }

    try:
        response = requests.post(
            BREVO_TRANSACTIONAL_EMAIL_URL,
            headers=headers,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
    except requests.Timeout:
        logger.error('Brevo email delivery timed out.')
        return False
    except requests.ConnectionError:
        logger.error('Brevo email delivery could not connect.')
        return False
    except requests.HTTPError as exc:
        response = exc.response
        status_code = response.status_code if response is not None else 'unknown'
        detail = response.text[:500] if response is not None else 'No response body.'
        logger.error('Brevo email delivery failed with HTTP status %s: %s', status_code, detail)
        return False
    except requests.RequestException:
        logger.exception('Brevo email delivery request failed.')
        return False

    return True


def send_focusforge_email_async(user, subject, heading, message, action_url=''):
    """Queue Brevo delivery on a daemon thread so web requests never wait for it."""
    recipient = (user.email or '').strip()
    if not recipient:
        return False

    # Tests exercise notification triggers but must never deliver real email.
    if 'test' in sys.argv:
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
            send_brevo_email(recipient, subject, html, strip_tags(html))
        except Exception:
            logger.exception('FocusForge email delivery failed for user id %s', user.pk)

    Thread(target=deliver, name='focusforge-email', daemon=True).start()
    return True
