from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    # get_or_create is safe for normal saves and avoids a duplicate profile
    # exception if account creation requests arrive close together.
    Profile.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def send_login_email(sender, request, user, **kwargs):
    # A brand-new account gets the welcome email on verification instead (see verification.activate).
    if getattr(user, 'skip_login_email', False):
        return
    from django.utils import dateformat, timezone
    from notifications.emailing import send_focusforge_email_async
    signed_in_at = timezone.localtime()
    details = [('Time', dateformat.format(signed_in_at, r'M j, Y \a\t g:i A'))]
    device = describe_device(request.META.get('HTTP_USER_AGENT', '') if request else '')
    if device:
        details.append(('Device', device))
    send_focusforge_email_async(
        user, 'FocusForge · Welcome back', 'Welcome back to FocusForge',
        'You just signed in. Your workspace is ready: choose one meaningful task and make progress today.', '/',
        action_label='Open your dashboard', preheader='New sign-in to your FocusForge account.', details=details,
        secondary_text='Not you?', secondary_label='Reset your password', secondary_url='/accounts/password-reset/',
    )


def describe_device(user_agent):
    """A short, human description like 'Chrome on Windows' (empty if unknown)."""
    agent = user_agent.lower()
    browsers = (('edg/', 'Edge'), ('opr/', 'Opera'), ('firefox/', 'Firefox'), ('chrome/', 'Chrome'), ('safari/', 'Safari'))
    systems = (('android', 'Android'), ('iphone', 'iPhone'), ('ipad', 'iPad'), ('windows', 'Windows'),
               ('mac os', 'macOS'), ('linux', 'Linux'))
    browser = next((name for key, name in browsers if key in agent), '')
    system = next((name for key, name in systems if key in agent), '')
    if browser and system:
        return f'{browser} on {system}'
    return browser or system
