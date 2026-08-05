from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Subject, StudySession, StudyFileLog
from .forms import SubjectForm, StudySessionForm


@login_required
def study_dashboard(request):
    subjects = Subject.objects.filter(user=request.user)
    sessions = StudySession.objects.filter(user=request.user)[:10]
    recent_files = StudyFileLog.objects.filter(user=request.user)[:10]

    if request.method == 'POST':
        form = StudySessionForm(request.POST, user=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = request.user
            session.save()
            messages.success(request, 'Study session logged.')
            return redirect('study:study_dashboard')
    else:
        form = StudySessionForm(user=request.user)

    return render(request, 'study/study_dashboard.html', {
        'subjects': subjects,
        'sessions': sessions,
        'recent_files': recent_files,
        'form': form,
    })


@login_required
def subject_create(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.user = request.user
            subject.save()
            messages.success(request, 'Subject added.')
            return redirect('study:study_dashboard')
    else:
        form = SubjectForm()
    return render(request, 'study/subject_form.html', {'form': form})