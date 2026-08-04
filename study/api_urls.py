from rest_framework.routers import DefaultRouter
from .api_views import SubjectViewSet, StudySessionViewSet, StudyFileLogViewSet

router = DefaultRouter()
router.register('subjects', SubjectViewSet, basename='subject')
router.register('study-sessions', StudySessionViewSet, basename='studysession')
router.register('study-file-logs', StudyFileLogViewSet, basename='studyfilelog')

urlpatterns = router.urls