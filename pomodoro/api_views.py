from rest_framework import viewsets, permissions
from .models import PomodoroSession
from .serializers import PomodoroSessionSerializer


class PomodoroSessionViewSet(viewsets.ModelViewSet):
    serializer_class = PomodoroSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PomodoroSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)