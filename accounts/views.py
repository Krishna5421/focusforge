from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import secrets
from tasks.models import Task
from habits.models import Habit, HabitLog
from goals.models import Goal, Milestone
from pomodoro.models import PomodoroSession
from study.models import StudySession
from .forms import (RegisterForm, StyledLoginForm, ProfileForm, UserUpdateForm,
                    PasswordResetRequestForm, PasswordResetOTPForm, PasswordResetSetForm)
from .models import PasswordResetOTP


def weekly_consistency_score(user, today=None):
    """Return this week's completed task and scheduled-habit percentage."""
    today = today or timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    weekly_tasks = Task.objects.filter(user=user, due_date__date__range=(week_start, today))
    expected_items = weekly_tasks.count()
    completed_items = weekly_tasks.filter(status='COMPLETED').count()

    habits = Habit.objects.filter(user=user, is_active=True, created_at__date__lte=today).prefetch_related('logs')
    for habit in habits:
        first_day = max(week_start, habit.created_at.date())
        completed_dates = set(habit.logs.filter(
            date__range=(first_day, today), completed=True,
        ).values_list('date', flat=True))

        if habit.frequency == 'WEEKLY' and not habit.target_days:
            expected_items += 1
            completed_items += int(bool(completed_dates))
            continue

        target_days = habit.target_days if habit.frequency == 'WEEKLY' else range(1, 8)
        scheduled_dates = {
            first_day + timedelta(days=offset)
            for offset in range((today - first_day).days + 1)
            if (first_day + timedelta(days=offset)).isoweekday() in target_days
        }
        expected_items += len(scheduled_dates)
        completed_items += len(completed_dates & scheduled_dates)

    return round((completed_items / expected_items) * 100) if expected_items else 0


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            user = register_form.save()
            login(request, user)
            messages.success(request, 'Account created successfully. Welcome to FocusForge!')
            return redirect('core:dashboard')
    else:
        register_form = RegisterForm()

    login_form = StyledLoginForm()
    return render(request, 'accounts/auth.html', {
        'login_form': login_form,
        'register_form': register_form,
        'initial_view': 'register',
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        login_form = StyledLoginForm(request, data=request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        login_form = StyledLoginForm()

    register_form = RegisterForm()
    return render(request, 'accounts/auth.html', {
        'login_form': login_form,
        'register_form': register_form,
        'initial_view': 'login',
    })


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier']
            user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=True).first()
            # Keep the response generic so an email address cannot be used to discover accounts.
            if user and user.email:
                code = f'{secrets.randbelow(1_000_000):06d}'
                PasswordResetOTP.objects.update_or_create(
                    user=user,
                    defaults={'code_hash': make_password(code), 'expires_at': timezone.now() + timedelta(minutes=10), 'attempts': 0},
                )
                from notifications.emailing import send_focusforge_email_async
                send_focusforge_email_async(user, 'FocusForge · Your password reset code', 'Your password reset code',
                                            f'Use this code to reset your password: {code}. It expires in 10 minutes. If you did not request this, you can safely ignore this email.')
                request.session['password_reset_user_id'] = user.pk
            messages.success(request, 'If an account matches those details, a 6-digit code has been sent to its email.')
            return redirect('accounts:password_reset_verify')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'accounts/password_reset.html', {'form': form})


def password_reset_verify(request):
    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        return redirect('accounts:password_reset')
    if request.method == 'POST':
        form = PasswordResetOTPForm(request.POST)
        if form.is_valid():
            otp = PasswordResetOTP.objects.filter(user_id=user_id).first()
            if not otp or otp.is_expired():
                form.add_error('otp', 'This code has expired. Request a new one.')
            elif otp.attempts >= 5:
                form.add_error('otp', 'Too many attempts. Request a new code.')
            elif not check_password(form.cleaned_data['otp'], otp.code_hash):
                otp.attempts += 1
                otp.save(update_fields=['attempts', 'created_at'])
                form.add_error('otp', 'That code is not correct.')
            else:
                otp.delete()
                request.session['password_reset_verified_user_id'] = user_id
                request.session.pop('password_reset_user_id', None)
                return redirect('accounts:password_reset_new_password')
    else:
        form = PasswordResetOTPForm()
    return render(request, 'accounts/password_reset_verify.html', {'form': form})


def password_reset_new_password(request):
    user_id = request.session.get('password_reset_verified_user_id')
    if not user_id:
        return redirect('accounts:password_reset')
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if not user:
        request.session.pop('password_reset_verified_user_id', None)
        return redirect('accounts:password_reset')
    if request.method == 'POST':
        form = PasswordResetSetForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.save(update_fields=['password'])
            request.session.pop('password_reset_verified_user_id', None)
            messages.success(request, 'Password updated. You can now log in.')
            return redirect('accounts:login')
    else:
        form = PasswordResetSetForm()
    return render(request, 'accounts/password_reset_new_password.html', {'form': form})


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {
        'profile': request.user.profile,
        'weekly_consistency_score': weekly_consistency_score(request.user),
    })


@login_required
def settings_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Settings updated successfully.')
            return redirect('accounts:settings')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    return render(request, 'accounts/settings.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@login_required
def export_data(request):
    user = request.user
    data = {
        'exported_at': timezone.now().isoformat(),
        'profile': {
            'username': user.username, 'first_name': user.first_name, 'last_name': user.last_name,
            'email': user.email, 'bio': user.profile.bio, 'total_xp': user.profile.total_xp,
            'current_streak': user.profile.current_streak,
        },
        'tasks': [{
            'title': task.title, 'description': task.description, 'category': task.category.name if task.category else None,
            'priority': task.priority, 'status': task.status, 'due_date': task.due_date.isoformat() if task.due_date else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'tags': list(task.tags.values_list('name', flat=True)),
        } for task in Task.objects.filter(user=user).prefetch_related('tags', 'category')],
        'habits': [{
            'name': habit.name, 'category': habit.category, 'frequency': habit.frequency,
            'current_streak': habit.current_streak, 'longest_streak': habit.longest_streak,
            'logs': [{'date': log.date.isoformat(), 'completed': log.completed} for log in habit.logs.all()],
        } for habit in Habit.objects.filter(user=user).prefetch_related('logs')],
        'goals': [{
            'title': goal.title, 'deadline': goal.deadline.isoformat(), 'progress': goal.completion_percentage,
            'status': goal.status, 'milestones': [{'title': item.title, 'completed': item.is_completed} for item in goal.milestones.all()],
        } for goal in Goal.objects.filter(user=user).prefetch_related('milestones')],
        'pomodoro_sessions': [{
            'task': session.task.title if session.task else None, 'planned_minutes': session.duration_minutes,
            'actual_seconds': session.actual_focus_seconds, 'status': session.status,
            'started_at': session.started_at.isoformat(),
        } for session in PomodoroSession.objects.filter(user=user).select_related('task')],
        'study_sessions': [{
            'subject': session.subject.name, 'date': session.date.isoformat(), 'planned_minutes': session.planned_minutes,
            'actual_seconds': session.actual_seconds, 'duration_minutes': session.duration_minutes,
            'resource_name': session.resource_name, 'notes': session.notes,
        } for session in StudySession.objects.filter(user=user).select_related('subject')],
    }
    response = JsonResponse(data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="focusforge-{user.username}-data.json"'
    return response
