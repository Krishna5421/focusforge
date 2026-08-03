from rest_framework.routers import DefaultRouter
from .api_views import GoalViewSet, MilestoneViewSet

router = DefaultRouter()
router.register('goals', GoalViewSet, basename='goal')
router.register('milestones', MilestoneViewSet, basename='milestone')

urlpatterns = router.urls