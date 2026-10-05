"""Permanent account deletion: the user's rows (all related data cascades) plus their uploaded files."""
import logging

from django.contrib.auth.models import User
from django.db import transaction

from study.models import ActiveStudySession, StudySession
from .models import Profile

logger = logging.getLogger(__name__)

CONFIRM_WORD = 'DELETE'


def can_self_delete(user):
    """Staff and superusers must be removed by another admin, so the owner can't lock themselves out."""
    return not (user.is_staff or user.is_superuser)


def uploaded_files(user):
    """Stored files that database deletion would leave behind (profile photo, study attachments)."""
    files = []
    profile = Profile.objects.filter(user=user).first()
    if profile and profile.profile_picture:
        files.append(profile.profile_picture)
    for model in (StudySession, ActiveStudySession):
        files += [item.resource_file for item in model.objects.filter(user=user).exclude(resource_file='')
                  if item.resource_file]
    return files


def remove_files(files):
    for field_file in files:
        try:
            field_file.storage.delete(field_file.name)
        except Exception:
            # The file may already be gone; account deletion must not fail because of it.
            logger.exception('Could not delete stored file %s during account deletion', field_file.name)


def delete_account(user):
    """Delete the user and everything linked to them. Files are removed only after the database commit."""
    files = uploaded_files(user)
    farewell = User(username=user.username, first_name=user.first_name, email=user.email, is_active=False)
    user_id = user.pk
    with transaction.atomic():
        user.delete()
        transaction.on_commit(lambda: remove_files(files))
    logger.info('User %s deleted their account', user_id)
    send_deletion_email(farewell)


def send_deletion_email(farewell):
    if not farewell.email:
        return
    from notifications.emailing import send_focusforge_email_async
    send_focusforge_email_async(
        farewell, 'Your FocusForge account was deleted', 'Your account has been deleted',
        'Your FocusForge account and all of its data have been permanently deleted. '
        'If you did not do this, reply to this email right away.', '',
        preheader='Your FocusForge account and data were permanently deleted.',
        footer_reason=f'This message was sent to {farewell.email} because the FocusForge account using it was deleted.',
    )
