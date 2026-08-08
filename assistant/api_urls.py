from django.urls import path
from .api_views import AssistantQueryAPIView

urlpatterns = [
    path('assistant/ask/', AssistantQueryAPIView.as_view(), name='api_assistant_ask'),
]