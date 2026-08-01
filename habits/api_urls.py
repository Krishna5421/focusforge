from rest_framework.routers import DefaultRouter
from .api_views import HabitViewSet, HabitLogViewSet

router = DefaultRouter()
router.register('habits', HabitViewSet, basename='habit')
router.register('habit-logs', HabitLogViewSet, basename='habitlog')

urlpatterns = router.urls