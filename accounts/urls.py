from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('verify-email/resend/', views.verify_email_resend, name='verify_email_resend'),
    path('verify-email/restart/', views.verify_email_restart, name='verify_email_restart'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('export/', views.export_data, name='export_data'),

    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password-reset/new-password/', views.password_reset_new_password, name='password_reset_new_password'),
]
