from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .utils import ask_assistant


class AssistantQueryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = request.data.get('question', '').strip()

        if not question:
            return Response({'error': 'Question is required.'}, status=status.HTTP_400_BAD_REQUEST)

        answer = ask_assistant(request.user, question)
        return Response({'answer': answer})