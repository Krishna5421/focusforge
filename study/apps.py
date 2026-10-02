from django.apps import AppConfig


class StudyConfig(AppConfig):
    name = 'study'

    def ready(self):
        import study.signals
