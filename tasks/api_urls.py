from rest_framework.routers import DefaultRouter
from .api_views import TaskViewSet, CategoryViewSet, TagViewSet

router = DefaultRouter()
router.register('tasks', TaskViewSet, basename='task')
router.register('categories', CategoryViewSet, basename='category')
router.register('tags', TagViewSet, basename='tag')

urlpatterns = router.urls