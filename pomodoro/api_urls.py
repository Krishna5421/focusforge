from rest_framework.routers import DefaultRouter
from .api_views import PomodoroSessionViewSet

router = DefaultRouter()
router.register('pomodoro-sessions', PomodoroSessionViewSet, basename='pomodorosession')

urlpatterns = router.urls