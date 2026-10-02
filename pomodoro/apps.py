from django.apps import AppConfig


class PomodoroConfig(AppConfig):
    name = 'pomodoro'

    def ready(self):
        import pomodoro.signals
