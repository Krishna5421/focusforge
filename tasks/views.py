from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Task
from .forms import TaskForm


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user, parent_task__isnull=True)

    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    search_query = request.GET.get('search')

    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if search_query:
        tasks = tasks.filter(title__icontains=search_query)

    return render(request, 'tasks/task_list.html', {'tasks': tasks})


@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            form.save_m2m()
            messages.success(request, 'Task created successfully.')
            return redirect('tasks:task_list')
    else:
        form = TaskForm(user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form})


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully.')
            return redirect('tasks:task_list')
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        task.delete()
        messages.info(request, 'Task deleted.')
    return redirect('tasks:task_list')


@login_required
def task_toggle_status(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if task.status == 'COMPLETED':
        task.status = 'PENDING'
        task.completed_at = None
    else:
        task.status = 'COMPLETED'
    task.save()
    return redirect('tasks:task_list')