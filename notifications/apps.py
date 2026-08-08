from django.apps import AppConfig
import sys
import os


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') == 'true':
            from .scheduler import start_scheduler
            start_scheduler()