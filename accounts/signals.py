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
    from notifications.emailing import send_focusforge_email_async
    send_focusforge_email_async(user, 'FocusForge · Welcome back', 'Welcome back to FocusForge',
                                'Your workspace is ready. Choose one meaningful task and make progress today.', '/')
