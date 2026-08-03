from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Goal, Milestone
from .forms import GoalForm, MilestoneForm


@login_required
def goal_list(request):
    goals = Goal.objects.filter(user=request.user)
    return render(request, 'goals/goal_list.html', {'goals': goals})


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
    return redirect('goals:goal_detail', pk=milestone.goal.pk)


@login_required
def goal_delete(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.info(request, 'Goal deleted.')
        return redirect('goals:goal_list')
    return render(request, 'goals/goal_confirm_delete.html', {'goal': goal})