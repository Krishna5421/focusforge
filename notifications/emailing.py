import logging
import sys
from threading import Thread

import requests
from django.conf import settings
from django.template.loader import render_to_string

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


def absolute_url(path):
    """Turn a site path into a full link that works from an email client."""
    if not path:
        return ''
    return f'{settings.SITE_URL}{path}' if path.startswith('/') else path


def render_focusforge_email(user, subject, heading, message, action_url='', *, action_label='Open FocusForge',
                            preheader='', code='', code_note='', details=None, steps=None, secondary_text='',
                            secondary_label='', secondary_url='', footer_reason=''):
    """Render the shared FocusForge email layout. Returns (html, plain_text)."""
    context = {
        'subject': subject,
        'name': user.first_name or user.username,
        'heading': heading,
        'message': message,
        'preheader': preheader or message[:110],
        'action_url': absolute_url(action_url),
        'action_label': action_label,
        'code': code,
        'code_note': code_note,
        'details': details or [],
        'steps': [{**step, 'url': absolute_url(step['url'])} for step in (steps or [])],
        'secondary_text': secondary_text,
        'secondary_label': secondary_label,
        'secondary_url': absolute_url(secondary_url),
        'footer_reason': footer_reason or f'You are receiving this because you have a FocusForge account ({user.email}).',
        'site_url': settings.SITE_URL,
        'settings_url': absolute_url('/accounts/settings/') if user.is_active else '',
        'site_name': 'FocusForge',
    }
    html = render_to_string('emails/focusforge_email.html', context)
    text = render_to_string('emails/focusforge_email.txt', context)
    return html, text


def send_focusforge_email_async(user, subject, heading, message, action_url='', **extras):
    """Queue Brevo delivery on a daemon thread so web requests never wait for it.

    `extras` are the optional layout pieces of render_focusforge_email (code, details, steps, ...).
    """
    recipient = (user.email or '').strip()
    if not recipient:
        return False

    # Tests exercise notification triggers but must never deliver real email.
    if 'test' in sys.argv:
        return False

    def deliver():
        try:
            html, text = render_focusforge_email(user, subject, heading, message, action_url, **extras)
            send_brevo_email(recipient, subject, html, text)
        except Exception:
            logger.exception('FocusForge email delivery failed for user id %s', user.pk)

    Thread(target=deliver, name='focusforge-email', daemon=True).start()
    return True
