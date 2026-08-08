from rest_framework.routers import DefaultRouter
from .api_views import NotificationViewSet

router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = router.urls