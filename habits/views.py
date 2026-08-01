from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Habit, HabitLog
from .forms import HabitForm


@login_required
def habit_list(request):
    habits = Habit.objects.filter(user=request.user, is_active=True)
    today = timezone.now().date()

    for habit in habits:
        habit.completed_today = habit.logs.filter(date=today, completed=True).exists()

    return render(request, 'habits/habit_list.html', {'habits': habits, 'today': today})


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
def habit_toggle_today(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = timezone.now().date()

    log = habit.logs.filter(date=today).first()
    if log:
        log.delete()
        messages.info(request, 'Marked as not done for today.')
    else:
        HabitLog.objects.create(habit=habit, date=today, completed=True)
        messages.success(request, 'Habit marked complete for today!')

    return redirect('habits:habit_list')


@login_required
def habit_delete(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        habit.is_active = False
        habit.save()
        messages.info(request, 'Habit removed.')
        return redirect('habits:habit_list')
    return render(request, 'habits/habit_confirm_delete.html', {'habit': habit})