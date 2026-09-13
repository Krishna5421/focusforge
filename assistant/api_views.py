from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .utils import ask_assistant, check_rate_limit, MAX_QUERIES
from .models import AIQueryLog
from django.utils import timezone


class AssistantQueryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = request.data.get('question', '').strip()

        if not question:
            return Response({'error': 'Question is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not check_rate_limit(request.user):
            return Response({
                'error': f'You have reached the {MAX_QUERIES} messages per day limit.',
                'usage': MAX_QUERIES,
                'limit': MAX_QUERIES,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        answer = ask_assistant(request.user, question)
        usage = AIQueryLog.objects.filter(user=request.user, created_at__date=timezone.localdate()).count()
        return Response({'answer': answer, 'usage': usage, 'limit': MAX_QUERIES})
