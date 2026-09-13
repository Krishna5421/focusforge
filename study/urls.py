from django.urls import path
from . import views

app_name = 'study'

urlpatterns = [
    path('', views.study_dashboard, name='study_dashboard'),
    path('subject/create/', views.subject_create, name='subject_create'),
    path('session/create/', views.study_session_create, name='study_session_create'),
    path('active/setup/', views.active_session_setup, name='active_session_setup'),
    path('active/save/', views.active_session_save, name='active_session_save'),
    path('active/<str:action>/', views.active_session_timer, name='active_session_timer'),
]
