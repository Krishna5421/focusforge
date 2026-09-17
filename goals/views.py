from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from django.db.models import Case, When, IntegerField
from .models import Goal, Milestone
from .forms import GoalForm, MilestoneForm


@login_required
def goal_list(request):
    goals = Goal.objects.filter(user=request.user).prefetch_related('milestones').order_by(
        Case(When(status='COMPLETED', then=1), default=0, output_field=IntegerField()),
        '-created_at',
    )
    search_query = request.GET.get('search', '').strip()
    if search_query:
        goals = goals.filter(title__icontains=search_query)
    return render(request, 'goals/goal_list.html', {
        'goals': goals,
        'search_query': search_query,
    })


@login_required
def goal_create(request):
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, 'Goal created successfully.')
            return redirect('goals:goal_detail', pk=goal.pk)
    else:
        form = GoalForm()
    return render(request, 'goals/goal_form.html', {'form': form})


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    milestones = goal.milestones.all()

    if request.method == 'POST':
        milestone_form = MilestoneForm(request.POST)
        if milestone_form.is_valid():
            milestone = milestone_form.save(commit=False)
            milestone.goal = goal
            milestone.save()
            messages.success(request, 'Milestone added.')
            return redirect('goals:goal_detail', pk=goal.pk)
    else:
        milestone_form = MilestoneForm()

    return render(request, 'goals/goal_detail.html', {
        'goal': goal,
        'milestones': milestones,
        'milestone_form': milestone_form,
    })


@login_required
def milestone_toggle(request, pk):
    milestone = get_object_or_404(Milestone, pk=pk, goal__user=request.user)
    milestone.is_completed = not milestone.is_completed
    if not milestone.is_completed:
        milestone.completed_at = None
    milestone.save()
    update_goal_progress(milestone.goal)
    record_goal_notifications(milestone)
    return redirect('goals:goal_detail', pk=milestone.goal.pk)


@login_required
def goal_delete(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.info(request, 'Goal deleted.')
    return redirect('goals:goal_list')


def update_goal_progress(goal):
    milestones = goal.milestones.all()
    total = milestones.count()
    completed = milestones.filter(is_completed=True).count()
    goal.completion_percentage = round((completed / total) * 100) if total else 0
    goal.status = 'COMPLETED' if total and completed == total else 'ACTIVE'
    goal.save(update_fields=['completion_percentage', 'status'])


def record_goal_notifications(milestone):
    if not milestone.is_completed:
        return
    from notifications.utils import notify_once
    goal = milestone.goal
    notify_once(goal.user, 'MILESTONE_COMPLETED', 'Milestone completed',
                f'{goal.title}: “{milestone.title}” is complete.', milestone.pk)
    if goal.status == 'COMPLETED':
        notify_once(goal.user, 'GOAL_COMPLETED', 'Goal completed!',
                    f'You completed “{goal.title}”.', goal.pk)
        from notifications.emailing import send_focusforge_email_async
        send_focusforge_email_async(goal.user, 'FocusForge · Goal completed!', 'You completed a goal!',
                                    f'Congratulations — “{goal.title}” is complete. Take a moment to celebrate your progress.', '/goals/')


def milestone_titles(value):
    return [title.strip() for title in value.splitlines() if title.strip()]


def save_goal_from_request(request, goal=None):
    title = request.POST.get('title', '').strip()
    deadline_value = request.POST.get('deadline', '')
    if not title:
        return None, 'Goal name is required.'
    try:
        deadline = datetime.strptime(deadline_value, '%Y-%m-%d').date()
    except ValueError:
        return None, 'Enter a valid deadline.'

    goal = goal or Goal(user=request.user)
    goal.title = title
    goal.deadline = deadline
    goal.description = ''
    goal.save()

    old_milestones = {milestone.title: milestone for milestone in goal.milestones.all()}
    titles = milestone_titles(request.POST.get('milestones', ''))
    kept_ids = []
    for order, title in enumerate(titles):
        milestone = old_milestones.pop(title, None)
        if milestone:
            milestone.order = order
            milestone.save(update_fields=['order'])
        else:
            milestone = Milestone.objects.create(goal=goal, title=title, order=order)
        kept_ids.append(milestone.pk)
    goal.milestones.exclude(pk__in=kept_ids).delete()
    update_goal_progress(goal)
    return goal, None


@login_required
def ajax_goal_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    goal, error = save_goal_from_request(request)
    if error:
        return JsonResponse({'error': error}, status=400)
    return JsonResponse({'success': True, 'goal_id': goal.pk})


@login_required
def ajax_goal_update(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    goal, error = save_goal_from_request(request, goal)
    if error:
        return JsonResponse({'error': error}, status=400)
    return JsonResponse({'success': True, 'goal_id': goal.pk})


@login_required
def ajax_goal_delete(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    goal.delete()
    return JsonResponse({'success': True})


@login_required
def ajax_milestone_toggle(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    milestone = get_object_or_404(Milestone, pk=pk, goal__user=request.user)
    milestone.is_completed = not milestone.is_completed
    milestone.completed_at = timezone.now() if milestone.is_completed else None
    milestone.save()
    update_goal_progress(milestone.goal)
    record_goal_notifications(milestone)
    return JsonResponse({
        'success': True,
        'completed': milestone.is_completed,
        'goal_progress': milestone.goal.completion_percentage,
        'goal_status': milestone.goal.status,
    })
