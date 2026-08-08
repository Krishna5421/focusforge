from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('deadlines/', views.deadlines, name='deadlines'),
    path('analytics/', views.analytics_page, name='analytics_page'),
]