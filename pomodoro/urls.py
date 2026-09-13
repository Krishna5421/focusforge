from django.urls import path
from . import views

app_name = 'pomodoro'

urlpatterns = [
    path('', views.pomodoro_page, name='pomodoro_page'),
    path('daily-goal/', views.update_daily_goal, name='update_daily_goal'),
    path('start/', views.pomodoro_start, name='pomodoro_start'),
    path('<int:pk>/update/', views.pomodoro_update, name='pomodoro_update'),
]
