from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/', include('accounts.urls')),
    path('tasks/', include('tasks.urls')),
    path('habits/', include('habits.urls')),
    path('goals/', include('goals.urls')),
    path('study/', include('study.urls')),
    path('pomodoro/', include('pomodoro.urls')),
    path('notifications/', include('notifications.urls')),
    path('achievements/', include('achievements.urls')),
    path('', include('core.urls')),

    path('api/auth/', include('accounts.api_urls')),
    path('api/', include('tasks.api_urls')),
    path('api/', include('habits.api_urls')),
    path('api/', include('goals.api_urls')),
    path('api/', include('study.api_urls')),
    path('api/', include('pomodoro.api_urls')),
    path('api/', include('notifications.api_urls')),
    path('api/', include('achievements.api_urls')),
    path('api/', include('core.api_urls')),
    path('assistant/', include('assistant.urls')),
    path('api/', include('assistant.api_urls')),
]

handler400 = 'core.error_views.bad_request'
handler403 = 'core.error_views.permission_denied'
handler404 = 'core.error_views.page_not_found'
handler500 = 'core.error_views.server_error'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
