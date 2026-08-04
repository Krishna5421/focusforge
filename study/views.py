from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Subject, StudySession, StudyFileLog
from .forms import SubjectForm, StudySessionForm

@login_required
def study_dashboard(request):
    pass

@login_required
def subject_create(request):
    pass

