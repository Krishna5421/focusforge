from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate with either the username or the account email (case-insensitive)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        identifier = (username if username is not None else kwargs.get(UserModel.USERNAME_FIELD) or '').strip()
        if not identifier or password is None:
            return None

        user = UserModel._default_manager.filter(username=identifier).first()
        if user is None and '@' in identifier:
            # Emails are unique at sign-up and in settings; if old data has duplicates, refuse rather than guess.
            matches = list(UserModel._default_manager.filter(email__iexact=identifier)[:2])
            user = matches[0] if len(matches) == 1 else None

        if user is None:
            # Run the hasher anyway so response time does not reveal whether the account exists.
            UserModel().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
