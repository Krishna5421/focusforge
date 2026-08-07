from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import UserAchievement
from .serializers import UserAchievementSerializer
from .utils import check_all_achievements


class UserAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserAchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserAchievement.objects.filter(user=self.request.user)


class AchievementCheckAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        check_all_achievements(request.user)
        unlocked = UserAchievement.objects.filter(user=request.user)
        serializer = UserAchievementSerializer(unlocked, many=True)
        return Response(serializer.data)