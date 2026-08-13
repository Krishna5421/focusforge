from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime
from .models import Task, Category, Tag
from .forms import TaskForm


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user, parent_task__isnull=True).select_related('category')

    # Stats
    total_tasks = tasks.count()
    pending_tasks = tasks.filter(status='PENDING').count()
    in_progress_tasks = tasks.filter(status='IN_PROGRESS').count()
    completed_tasks = tasks.filter(status='COMPLETED').count()
    overdue_tasks = tasks.filter(
        due_date__lt=timezone.now(),
        status__in=['PENDING', 'IN_PROGRESS']
    ).count()

    # Priority breakdown
    high_priority = tasks.filter(priority='HIGH').count()
    medium_priority = tasks.filter(priority='MEDIUM').count()
    low_priority = tasks.filter(priority='LOW').count()

    def percent(val):
        return round((val / total_tasks * 100)) if total_tasks else 0

    # Filters
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search')

    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if category_filter:
        tasks = tasks.filter(category_id=category_filter)
    if search_query:
        tasks = tasks.filter(title__icontains=search_query)

    # Upcoming deadlines
    upcoming_tasks = Task.objects.filter(
        user=request.user,
        due_date__isnull=False,
        status__in=['PENDING', 'IN_PROGRESS']
    ).order_by('due_date')[:5]

    # Category stats
    categories = Category.objects.filter(user=request.user)
    category_stats = []
    category_icons = {
        'work': 'bi-briefcase', 'study': 'bi-book', 'personal': 'bi-person',
        'health': 'bi-heart', 'fitness': 'bi-lightning', 'finance': 'bi-currency-dollar'
    }
    for cat in categories:
        count = Task.objects.filter(user=request.user, category=cat).count()
        category_stats.append({
            'name': cat.name,
            'color': cat.color,
            'count': count,
            'percent': percent(count),
            'icon': category_icons.get(cat.name.lower(), 'bi-folder')
        })

    context = {
        'tasks': tasks,
        'categories': categories,
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'low_priority': low_priority,
        'high_priority_percent': percent(high_priority),
        'medium_priority_percent': percent(medium_priority),
        'low_priority_percent': percent(low_priority),
        'upcoming_tasks': upcoming_tasks,
        'category_stats': category_stats,
    }
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_create(request):
    # Get or create default categories
    default_cats = ['Work', 'Personal', 'Study', 'Other']
    categories = []
    
    for cat_name in default_cats:
        cat, created = Category.objects.get_or_create(
            user=request.user,
            name=cat_name,
            defaults={'color': '#2dd4bf'}
        )
        categories.append(cat)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        
        if form.is_valid():
            # 1. Save task without committing to get the ID
            task = form.save(commit=False)
            task.user = request.user
            
            # 2. Handle separate Date and Time inputs
            date_val = request.POST.get('due_date')
            time_val = request.POST.get('due_time')
            if date_val:
                if time_val:
                    task.due_date = datetime.strptime(f"{date_val} {time_val}", "%Y-%m-%d %H:%M")
                else:
                    task.due_date = datetime.strptime(date_val, "%Y-%m-%d").replace(hour=23, minute=59)
            
            # 3. Save the task to the database
            task.save()
            
            # 4. Handle Tags (Text input -> ManyToMany)
            tags_input = request.POST.get('tags', '')
            if tags_input:
                tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
                for name in tag_names:
                    tag_obj, created = Tag.objects.get_or_create(
                        name=name, 
                        defaults={'user': request.user}
                    )
                    task.tags.add(tag_obj)
            
            messages.success(request, 'Task created successfully.')
            return redirect('tasks:task_list')
        else:
            print("❌ FORM ERRORS:", form.errors)
            messages.error(request, 'Please fix the errors below.')
    else:
        form = TaskForm(user=request.user)
        
    return render(request, 'tasks/task_form.html', {'form': form, 'categories': categories})


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


# AJAX endpoints
@login_required
def ajax_toggle_status(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if task.status == 'COMPLETED':
        task.status = 'PENDING'
        task.completed_at = None
    else:
        task.status = 'COMPLETED'
    task.save()
    return JsonResponse({
        'success': True,
        'status': task.status,
        'status_display': task.get_status_display(),
    })


@login_required
def ajax_delete_task(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete()
    return JsonResponse({'success': True})