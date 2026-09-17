from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.db import IntegrityError, transaction
from datetime import timedelta
from xml.sax.saxutils import escape
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
            try:
                with transaction.atomic():
                    user = register_form.save()
            except IntegrityError:
                # A second, near-simultaneous registration can pass validation
                # before the first request commits. Keep this a field error.
                register_form.add_error('username', 'This username is already in use. Please choose another one.')
            else:
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
                messages.success(request, 'Password reset email sent successfully.')
                return redirect('accounts:password_reset_verify')
            form.add_error('identifier', 'No account was found with those details.')
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
    period = request.GET.get('period', 'weekly')
    today = timezone.localdate()
    if period == 'monthly':
        start_date = today.replace(day=1)
        period_label = today.strftime('%B %Y')
    else:
        period = 'weekly'
        start_date = today - timedelta(days=today.weekday())
        period_label = f'{start_date:%b %d} - {today:%b %d, %Y}'

    completed_tasks = Task.objects.filter(
        user=user, status='COMPLETED', completed_at__date__range=(start_date, today),
    ).order_by('-completed_at')
    habit_checkins = HabitLog.objects.filter(
        habit__user=user, completed=True, date__range=(start_date, today),
    ).count()
    focus_sessions = PomodoroSession.objects.filter(
        user=user, status='COMPLETED', completed_at__date__range=(start_date, today),
    ).select_related('task')
    focus_seconds = sum(session.actual_focus_seconds or session.duration_minutes * 60 for session in focus_sessions)
    study_minutes = sum(session.duration_minutes for session in StudySession.objects.filter(
        user=user, date__range=(start_date, today),
    ))

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="focusforge-{period}-report.pdf"'
    document = SimpleDocTemplate(response, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                                 topMargin=16 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle('FocusForgeTitle', parent=styles['Title'], textColor=colors.white, fontSize=25, leading=30, spaceAfter=2)
    eyebrow = ParagraphStyle('FocusForgeEyebrow', parent=styles['Normal'], textColor=colors.HexColor('#fbbf24'), fontSize=8, leading=11, fontName='Helvetica-Bold', spaceAfter=5)
    subtitle = ParagraphStyle('FocusForgeSubtitle', parent=styles['Normal'], textColor=colors.HexColor('#7b8aa3'), fontSize=9, leading=14)
    heading = ParagraphStyle('FocusForgeHeading', parent=styles['Heading2'], textColor=colors.HexColor('#162235'), fontSize=14, leading=18, fontName='Helvetica-Bold', spaceBefore=17, spaceAfter=8)
    body = ParagraphStyle('FocusForgeBody', parent=styles['BodyText'], textColor=colors.HexColor('#42526b'), fontSize=9, leading=14)
    metric = ParagraphStyle('FocusForgeMetric', parent=body, alignment=TA_CENTER, fontSize=9, leading=14)
    metric_value = ParagraphStyle('FocusForgeMetricValue', parent=metric, textColor=colors.HexColor('#142033'), fontSize=20, leading=25, fontName='Helvetica-Bold')

    metrics = [
        ('Tasks completed', str(completed_tasks.count())),
        ('Habit check-ins', str(habit_checkins)),
        ('Focus time', f'{focus_seconds // 3600}h {(focus_seconds % 3600) // 60}m'),
        ('Study time', f'{study_minutes // 60}h {study_minutes % 60}m'),
    ]
    if period == 'weekly':
        metrics.append(('Weekly consistency', f'{weekly_consistency_score(user)}%'))

    display_name = user.get_full_name() or user.username
    header = Table([[
        [Paragraph('PERSONAL PRODUCTIVITY REPORT', eyebrow), Paragraph('FocusForge', title), Paragraph(f'{escape(display_name)}  |  {period_label}', ParagraphStyle('FocusForgeHeaderSub', parent=subtitle, textColor=colors.HexColor('#b6c3d7')))]
    ]], colWidths=[170 * mm])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#101827')),
        ('BOX', (0, 0), (-1, -1), 0, colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 18), ('RIGHTPADDING', (0, 0), (-1, -1), 18),
        ('TOPPADDING', (0, 0), (-1, -1), 16), ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
    ]))
    story = [header, Spacer(1, 7 * mm), Paragraph('At a glance', heading)]

    metric_rows = []
    for index in range(0, len(metrics), 3):
        group = metrics[index:index + 3]
        cells = []
        for label, value in group:
            cells.append([Paragraph(escape(label), metric), Paragraph(escape(value), metric_value)])
        while len(cells) < 3:
            cells.append('')
        metric_rows.append(cells)
    metric_table = Table(metric_rows, colWidths=[(170 * mm) / 3] * 3, hAlign='LEFT')
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7f9fc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dce4ef')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dce4ef')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.extend([metric_table, Paragraph('Completed tasks', heading)])
    if completed_tasks:
        rows = [[Paragraph('<b>Task</b>', body), Paragraph('<b>Completed</b>', body)]]
        rows.extend([
            [Paragraph(escape(task.title), body), Paragraph(timezone.localtime(task.completed_at).strftime('%b %d'), body)]
            for task in completed_tasks[:12]
        ])
        task_table = Table(rows, colWidths=[125 * mm, 45 * mm])
        task_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#18263a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#dce4ef')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        story.append(task_table)
    else:
        story.append(Paragraph('No completed tasks in this period yet.', body))

    story.extend([
        Paragraph('Progress snapshot', heading),
        Paragraph(f'You completed <b>{habit_checkins}</b> habit check-in(s), logged <b>{focus_seconds // 60}</b> focus minute(s), and studied for <b>{study_minutes}</b> minute(s) during this period.', body),
    ])

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#dce4ef'))
        canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
        canvas.setFillColor(colors.HexColor('#7b8aa3'))
        canvas.setFont('Helvetica', 8)
        canvas.drawString(18 * mm, 8 * mm, 'FocusForge  •  Build better days, one session at a time.')
        canvas.drawRightString(192 * mm, 8 * mm, f'Page {doc.page}')
        canvas.restoreState()

    document.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    return response
