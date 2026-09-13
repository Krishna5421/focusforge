from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Notification


@login_required
def notification_list(request):
    notification_styles = {
        'ACHIEVEMENT_UNLOCKED': ('bi-award', 'purple'), 'TASK_REMINDER': ('bi-check2', 'blue'),
        'TASK_COMPLETED': ('bi-check2-circle', 'blue'), 'GOAL_DEADLINE': ('bi-bullseye', 'purple'),
        'GOAL_COMPLETED': ('bi-trophy', 'purple'), 'MILESTONE_COMPLETED': ('bi-flag', 'purple'),
        'FOCUS_COMPLETED': ('bi-clock-history', 'amber'), 'POMODORO_ABANDONED': ('bi-stopwatch', 'amber'),
        'HABIT_COMPLETED': ('bi-heart', 'green'), 'STREAK_MILESTONE': ('bi-fire', 'green'),
        'STUDY_COMPLETED': ('bi-book', 'blue'),
        'STUDY_REMINDER': ('bi-bookmark', 'amber'),
    }
    notifications = Notification.objects.filter(user=request.user)
    for notification in notifications:
        notification.icon, notification.accent = notification_styles.get(notification.type, ('bi-bell', 'blue'))
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count(),
    })


@login_required
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications:notification_list')


@login_required
def notification_mark_all_read(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method.'}, status=405)
    updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True, 'updated': updated})


@login_required
def notification_clear_all(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method.'}, status=405)
    deleted, _ = Notification.objects.filter(user=request.user).delete()
    return JsonResponse({'success': True, 'deleted': deleted})
