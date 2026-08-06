from django.urls import path
from . import views

app_name = 'achievements'

urlpatterns = [
    path('', views.achievement_list, name='achievement_list'),
]