from django.urls import path
from . import views

app_name = 'habits'

urlpatterns = [
    path('', views.habit_list, name='habit_list'),
    path('create/', views.habit_create, name='habit_create'),
    path('<int:pk>/edit/', views.habit_update, name='habit_update'),  # NEW
    path('<int:pk>/toggle/', views.habit_toggle_today, name='habit_toggle_today'),
    path('ajax/<int:pk>/toggle/', views.ajax_toggle_habit, name='ajax_toggle_habit'),
    path('api/completion/<str:date_str>/', views.api_completion_status, name='api_completion_status'),
    path('<int:pk>/delete/', views.habit_delete, name='habit_delete'),
]