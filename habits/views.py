# habits/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.db.models import Count
from .models import Habit, HabitLog
from .forms import HabitForm
from .schedule import annotate_habits, month_summary


@login_required
def habit_list(request):
    today = timezone.localdate()
    all_habits, due_done, due_total = annotate_habits(request.user, today)

    total_habits = len(all_habits)
    completed_today_count = sum(1 for h in all_habits if h.completed_today)
    active_streaks = sum(1 for h in all_habits if h.current_streak > 0)
    best_streak = max((h.longest_streak for h in all_habits), default=0)
    daily_count = sum(1 for h in all_habits if h.frequency == 'DAILY')
    weekly_count = total_habits - daily_count

    start_date = today - timedelta(days=89)
    completion_counts = {
        item['date']: item['count']
        for item in HabitLog.objects.filter(
            habit__user=request.user,
            habit__is_active=True,
            completed=True,
            date__gte=start_date,
            date__lte=today,
        ).values('date').annotate(count=Count('id'))
    }
    activity_days = []
    for offset in range(89, -1, -1):
        day = today - timedelta(days=offset)
        count = completion_counts.get(day, 0)
        if not total_habits or not count:
            level = 0
        else:
            level = min(4, max(1, round((count / total_habits) * 4)))
        activity_days.append({'date': day, 'count': count, 'level': level})

    month = month_summary(request.user, all_habits, today)

    habits = all_habits
    search_query = request.GET.get('search', '').strip()
    frequency_filter = request.GET.get('frequency')
    if search_query:
        habits = [h for h in habits if search_query.lower() in h.name.lower()]
    if frequency_filter:
        habits = [h for h in habits if h.frequency == frequency_filter]

    category_labels = dict(Habit.CATEGORY_CHOICES)
    used_categories = sorted({h.category for h in all_habits}, key=lambda key: category_labels.get(key, key))

    context = {
        'habits': habits,
        'due_habits': [h for h in habits if h.due_today],
        'other_habits': [h for h in habits if not h.due_today],
        'due_done': due_done,
        'due_total': due_total,
        'due_percent': round(due_done / due_total * 100) if due_total else 0,
        'today': today,
        'total_habits': total_habits,
        'completed_today_count': completed_today_count,
        'active_streaks': active_streaks,
        'best_streak': best_streak,
        'daily_count': daily_count,
        'weekly_count': weekly_count,
        'activity_days': activity_days,
        'month': month,
        'habit_categories': Habit.CATEGORY_CHOICES,
        'filter_categories': [(key, category_labels.get(key, key).split(' & ')[0]) for key in used_categories],
        'search_query': search_query,
    }
    return render(request, 'habits/habit_list.html', context)


@login_required
def habit_create(request):
    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, 'Habit created successfully.')
            return redirect('habits:habit_list')
    else:
        form = HabitForm()
    return render(request, 'habits/habit_form.html', {'form': form})

@login_required
def habit_update(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = HabitForm(request.POST, instance=habit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Habit updated successfully.')
            return redirect('habits:habit_list')
    else:
        form = HabitForm(instance=habit)
        
    return render(request, 'habits/habit_form.html', {'form': form, 'habit': habit})


@login_required
def habit_toggle_today(request, pk):
    """Original sync toggle (kept for fallback/non-AJAX use)"""
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = timezone.localdate()

    log = habit.logs.filter(date=today).first()
    if log:
        log.delete()
        messages.info(request, 'Marked as not done for today.')
    else:
        HabitLog.objects.create(habit=habit, date=today, completed=True)
        messages.success(request, 'Habit marked complete for today! +XP')

    return redirect('habits:habit_list')


@login_required
def habit_delete(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        habit.is_active = False
        habit.save()
        messages.info(request, 'Habit removed.')
    return redirect('habits:habit_list')


# =========================================
# AJAX ENDPOINTS (For instant UI updates)
# =========================================

@login_required
def ajax_toggle_habit(request, pk):
    """
    AJAX endpoint for toggling habit completion without page reload.
    Returns JSON with updated stats for live UI updates.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = timezone.localdate()
    
    # Toggle the log
    log = habit.logs.filter(date=today).first()
    if log:
        log.delete()
        completed = False
    else:
        HabitLog.objects.create(habit=habit, date=today, completed=True)
        completed = True
    
    # Refresh habit from DB to get updated streak (signals.py handles streak recalc)
    habit.refresh_from_db()
    
    # Recalculate dashboard stats
    habits = Habit.objects.filter(user=request.user, is_active=True)
    completed_today_count = sum(
        1 for h in habits 
        if h.logs.filter(date=today, completed=True).exists()
    )
    active_streaks = sum(1 for h in habits if h.current_streak > 0)
    best_streak = max((h.longest_streak for h in habits), default=0)
    activity_count = HabitLog.objects.filter(habit__user=request.user, date=today, completed=True).count()
    activity_level = min(4, max(1, round((activity_count / habits.count()) * 4))) if habits.exists() and activity_count else 0
    
    annotated, due_done, due_total = annotate_habits(request.user, today)
    this_habit = next((h for h in annotated if h.pk == habit.pk), None)

    return JsonResponse({
        'success': True,
        'completed': completed,
        'streak': habit.current_streak,
        'longest_streak': habit.longest_streak,
        'due_done': due_done,
        'due_total': due_total,
        'all_done': bool(due_total) and due_done == due_total,
        'completion_rate': this_habit.rate if this_habit else 0,
        'month': {key: value for key, value in month_summary(request.user, annotated, today).items() if key != 'best_day'},
        'completed_today_count': completed_today_count,
        'active_streaks': active_streaks,
        'best_streak': best_streak,
        'completion_rate': habit.completion_rate(),
        'activity_count': activity_count,
        'activity_level': activity_level,
    })


def save_habit_from_request(request, habit=None):
    name = request.POST.get('name', '').strip()
    if not name:
        return None, 'Habit name is required.'

    category = request.POST.get('category', 'other')
    if category not in dict(Habit.CATEGORY_CHOICES):
        category = 'other'
    frequency = request.POST.get('frequency', 'DAILY')
    if frequency not in dict(Habit.FREQUENCY_CHOICES):
        frequency = 'DAILY'

    target_values = request.POST.getlist('target_days')
    # Continue accepting existing comma-separated form/API submissions while
    # validating every day and storing only integers in JSONField.
    target_values = [part.strip() for value in target_values for part in value.split(',') if part.strip()]
    if any(not value.isdigit() or not 1 <= int(value) <= 7 for value in target_values):
        return None, 'Choose weekdays from Monday (1) through Sunday (7).'
    target_days = sorted({int(value) for value in target_values})
    if frequency == 'DAILY' and target_days:
        return None, 'Target days only apply to weekly habits. Choose Weekly or clear the selected days.'

    habit = habit or Habit(user=request.user)
    habit.name = name
    habit.category = category
    habit.frequency = frequency
    habit.target_days = target_days
    if habit.pk:
        habit.icon = ''
    habit.save()
    return habit, None


@login_required
def ajax_habit_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    habit, error = save_habit_from_request(request)
    if error:
        return JsonResponse({'error': error}, status=400)
    return JsonResponse({'success': True, 'habit_id': habit.pk})


@login_required
def ajax_habit_update(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    habit, error = save_habit_from_request(request, habit)
    if error:
        return JsonResponse({'error': error}, status=400)
    return JsonResponse({'success': True, 'habit_id': habit.pk})


@login_required
def ajax_habit_delete(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    habit.is_active = False
    habit.save(update_fields=['is_active'])
    return JsonResponse({'success': True})


@login_required
def api_completion_status(request, date_str):
    """
    API endpoint for the calendar widget to fetch real completion data.
    Returns whether any habits were completed on the given date.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        completed_count = HabitLog.objects.filter(
            habit__user=request.user,
            habit__is_active=True,
            date=date,
            completed=True
        ).count()
        
        total_habits = Habit.objects.filter(user=request.user, is_active=True).count()
        
        return JsonResponse({
            'has_completion': completed_count > 0,
            'count': completed_count,
            'total': total_habits,
            'rate': round((completed_count / total_habits * 100), 1) if total_habits > 0 else 0
        })
    except (ValueError, TypeError):
        return JsonResponse({'has_completion': False, 'count': 0, 'total': 0, 'rate': 0})
