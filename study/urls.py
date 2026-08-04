from django.urls import path
from . import views

app_name = 'study'

urlpatterns = [
    path('', views.study_dashboard, name='study_dashboard'),
    path('subject/create/', views.subject_create, name='subject_create'),
]