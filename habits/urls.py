from django.urls import path
from . import views

app_name = 'habits'

urlpatterns = [
    path('', views.habit_list, name='habit_list'),
    path('create/', views.habit_create, name='habit_create'),
    path('<int:pk>/toggle/', views.habit_toggle_today, name='habit_toggle_today'),
    path('<int:pk>/delete/', views.habit_delete, name='habit_delete'),
]