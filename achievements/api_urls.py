from django.urls import path
from rest_framework.routers import DefaultRouter
from .api_views import UserAchievementViewSet, AchievementCheckAPIView

router = DefaultRouter()
router.register('user-achievements', UserAchievementViewSet, basename='userachievement')

urlpatterns = router.urls + [
    path('achievements/check/', AchievementCheckAPIView.as_view(), name='achievement_check'),
]