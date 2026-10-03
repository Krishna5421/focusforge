from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.db.models import Q
from . import verification
from .streaks import refresh_activity_streak
from .serializers import UserSerializer, RegisterSerializer, ProfileSerializer


class RegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        verification.purge_stale_unverified()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        sent = verification.send_verification_code(user)
        return Response({
            **serializer.data,
            'verification_required': True,
            'email_sent': sent,
            'detail': ('We emailed a 6-digit code. Confirm it at /api/auth/verify-email/ to activate the account.' if sent
                       else "We couldn't send the verification email. Request a new code at /api/auth/verify-email/resend/."),
        }, status=status.HTTP_201_CREATED)


def pending_user_for(identifier):
    identifier = (identifier or '').strip()
    if not identifier:
        return None
    user = User.objects.filter(Q(username=identifier) | Q(email__iexact=identifier), is_active=False).first()
    return user if verification.is_pending(user) else None


class VerifyEmailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user = pending_user_for(request.data.get('email') or request.data.get('username'))
        code = str(request.data.get('code', '')).strip()
        if user is None or not (len(code) == 6 and code.isdigit()):
            return Response({'detail': 'Enter the 6-digit code for an account waiting for verification.'},
                            status=status.HTTP_400_BAD_REQUEST)
        result, attempts_left = verification.verify_code(user, code)
        if result == verification.VERIFIED:
            return Response({'detail': 'Email verified. You can now log in.'})
        messages = {
            verification.INVALID: f'That code is incorrect. {attempts_left} attempt(s) left.',
            verification.EXPIRED: 'This code has expired. Request a new one.',
            verification.LOCKED: 'Too many incorrect attempts. Request a new code.',
        }
        return Response({'detail': messages.get(result, 'Request a new code.'), 'result': result},
                        status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user = pending_user_for(request.data.get('email') or request.data.get('username'))
        # Same reply whether or not the account exists, so this cannot be used to look up emails.
        reply = {'detail': 'If that account is waiting for verification, a new code has been sent.'}
        if user is None:
            return Response(reply)
        wait = verification.resend_wait_seconds(user)
        if wait:
            return Response({'detail': f'Please wait {wait} seconds before requesting another code.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        if not verification.send_verification_code(user):
            return Response({'detail': "We couldn't send the code right now. Please try again shortly."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(reply)


class ProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return refresh_activity_streak(self.request.user)


class MeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)