from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Case, When, IntegerField
from datetime import datetime
from .models import Task, Category, Tag
from .forms import TaskForm


END_OF_DAY = '23:59'


class DueDateError(ValueError):
    """A due date/time the user must correct; the message is safe to show."""


def keeps_existing_due_date(date_value, time_value, existing_due_date):
    """Allow an overdue task to be edited without forcing its date or time forward."""
    if existing_due_date is None:
        return False
    existing = timezone.localtime(existing_due_date)
    return (date_value == existing.strftime('%Y-%m-%d')
            and (not time_value or time_value == existing.strftime('%H:%M')))


def build_due_date(date_value, time_value='', existing_due_date=None):
    """Combine the date and optional time inputs; no time means end of day."""
    date_value = (date_value or '').strip()
    time_value = (time_value or '').strip()
    if not date_value:
        if time_value:
            raise DueDateError('Choose a due date for the selected time.')
        return None
    if keeps_existing_due_date(date_value, time_value, existing_due_date):
        return existing_due_date
    try:
        parsed = datetime.strptime(f'{date_value} {time_value or END_OF_DAY}', '%Y-%m-%d %H:%M')
    except ValueError:
        raise DueDateError('Enter a valid due date and time.')
    due_date = timezone.make_aware(parsed, timezone.get_current_timezone())
    if due_date.date() < timezone.localdate():
        raise DueDateError('Choose today or a future due date.')
    if due_date <= timezone.now():
        raise DueDateError('That time has already passed. Choose a later time.')
    return due_date


def parse_form_due_date(request, existing_due_date=None):
    return build_due_date(request.POST.get('due_date'), request.POST.get('due_time'), existing_due_date)


@login_required
def task_list(request):
    for name in ['Work', 'Personal', 'Study', 'Other']:
        Category.objects.get_or_create(user=request.user, name=name, defaults={'color': '#8b5cf6'})

    tasks = Task.objects.filter(user=request.user, parent_task__isnull=True).select_related('category').prefetch_related('tags')

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
    page_filter = request.GET.get('filter')

    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if category_filter:
        tasks = tasks.filter(category_id=category_filter)
    if search_query:
        tasks = tasks.filter(title__icontains=search_query)
    today = timezone.localdate()
    if page_filter == 'today':
        tasks = tasks.filter(due_date__date=today)
    elif page_filter == 'upcoming':
        tasks = tasks.filter(due_date__date__gt=today, status__in=['PENDING', 'IN_PROGRESS'])
    elif page_filter == 'overdue':
        tasks = tasks.filter(due_date__lt=timezone.now(), status__in=['PENDING', 'IN_PROGRESS'])
    elif page_filter == 'completed':
        tasks = tasks.filter(status='COMPLETED')
    tasks = tasks.order_by(
        Case(When(status='COMPLETED', then=1), default=0, output_field=IntegerField()),
        '-created_at',
    )

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
        'today': today,
        'now': timezone.now(),
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
            task = form.save(commit=False)
            task.user = request.user
            try:
                task.due_date = parse_form_due_date(request)
            except DueDateError as error:
                form.add_error(None, str(error))
                return render(request, 'tasks/task_form.html', {
                    'form': form, 'categories': categories, 'today': timezone.localdate(),
                })
            
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
        
    return render(request, 'tasks/task_form.html', {
        'form': form, 'categories': categories, 'today': timezone.localdate(),
    })


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            updated_task = form.save(commit=False)
            try:
                updated_task.due_date = parse_form_due_date(request, existing_due_date=task.due_date)
            except DueDateError as error:
                form.add_error(None, str(error))
            else:
                updated_task.save()
                form.save_m2m()
                messages.success(request, 'Task updated successfully.')
                return redirect('tasks:task_list')
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form, 'today': timezone.localdate()})


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


def save_task_from_request(request, task=None):
    title = request.POST.get('title', '').strip()
    if not title:
        return None, 'Title is required.'

    category = None
    category_id = request.POST.get('category')
    if category_id:
        category = get_object_or_404(Category, pk=category_id, user=request.user)

    priority = request.POST.get('priority', 'MEDIUM')
    if priority not in dict(Task.PRIORITY_CHOICES):
        priority = 'MEDIUM'

    try:
        due_date = parse_form_due_date(request, task.due_date if task else None)
    except DueDateError as error:
        return None, str(error)

    task = task or Task(user=request.user)
    task.title = title
    task.category = category
    task.priority = priority
    task.description = request.POST.get('description', '').strip()
    task.due_date = due_date
    task.save()

    tags = [name.strip() for name in request.POST.get('tags', '').split(',') if name.strip()]
    task.tags.clear()
    for name in tags:
        tag, created = Tag.objects.get_or_create(user=request.user, name=name)
        task.tags.add(tag)
    return task, None


@login_required
def ajax_task_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    task, error = save_task_from_request(request)
    if error:
        return JsonResponse({'error': error}, status=400)
    return JsonResponse({'success': True, 'task_id': task.pk})


@login_required
def ajax_task_update(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task, error = save_task_from_request(request, task)
    if error:
        return JsonResponse({'error': error}, status=400)
    return JsonResponse({'success': True, 'task_id': task.pk})


@login_required
def ajax_bulk_tasks(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    task_ids = request.POST.getlist('task_ids[]')
    tasks = Task.objects.filter(user=request.user, pk__in=task_ids)
    action = request.POST.get('action')

    if action == 'complete':
        for task in tasks.exclude(status='COMPLETED'):
            task.status = 'COMPLETED'
            task.save()
    elif action == 'delete':
        tasks.delete()
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)
    return JsonResponse({'success': True})
