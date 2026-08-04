from django.contrib import admin
from .models import Subject, StudySession, StudyFileLog

admin.site.register(Subject)
admin.site.register(StudySession)
admin.site.register(StudyFileLog)