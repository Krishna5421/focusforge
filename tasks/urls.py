from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('create/', views.task_create, name='task_create'),
    path('<int:pk>/edit/', views.task_update, name='task_update'),
    path('<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('<int:pk>/toggle/', views.task_toggle_status, name='task_toggle_status'),
    path('ajax/<int:pk>/toggle/', views.ajax_toggle_status, name='ajax_toggle_status'),
    path('ajax/<int:pk>/delete/', views.ajax_delete_task, name='ajax_delete_task'),
]