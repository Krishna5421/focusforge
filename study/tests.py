from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Subject, StudySession, ActiveStudySession


class StudyDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')
        self.subject = Subject.objects.create(user=self.user, name='Algorithms')
        self.client.login(username='student', password='password')

    def test_session_creation_saves_filename_not_a_file(self):
        response = self.client.post(reverse('study:study_session_create'), {
            'subject_name': self.subject.name,
            'duration_minutes': 45,
            'resource_name': 'sorting-notes.pdf',
            'notes': 'Reviewed quicksort.',
        })

        self.assertEqual(response.status_code, 200)
        session = StudySession.objects.get(pk=response.json()['id'])
        self.assertEqual(session.resource_name, 'sorting-notes.pdf')
        self.assertEqual(session.duration_minutes, 45)

    def test_typed_subject_never_uses_another_users_subject(self):
        foreign_subject = Subject.objects.create(user=self.other_user, name='Private subject')
        response = self.client.post(reverse('study:study_session_create'), {
            'subject_name': foreign_subject.name,
            'duration_minutes': 25,
        })

        self.assertEqual(response.status_code, 200)
        session = StudySession.objects.get(user=self.user)
        self.assertNotEqual(session.subject, foreign_subject)
        self.assertEqual(session.subject.name, 'Private subject')

    def test_subject_creation_returns_json_for_modal(self):
        response = self.client.post(reverse('study:subject_create'), {
            'name': 'Systems Design', 'color': '#f59e0b',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Systems Design')
        self.assertTrue(Subject.objects.filter(user=self.user, name='Systems Design').exists())

    def test_dashboard_shows_study_summary(self):
        StudySession.objects.create(user=self.user, subject=self.subject, date='2026-09-05', duration_minutes=45)
        response = self.client.get(reverse('study:study_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Study Sessions')
        self.assertContains(response, 'Algorithms')

    def test_setup_persists_active_session_across_refresh(self):
        response = self.client.post(reverse('study:active_session_setup'), {
            'subject_name': 'Databases', 'planned_minutes': 30,
            'resource_name': 'normalization.pdf', 'notes': 'Review normal forms.',
        })

        self.assertEqual(response.status_code, 200)
        active = ActiveStudySession.objects.get(user=self.user)
        self.assertEqual(active.subject.name, 'Databases')
        self.assertEqual(active.remaining_seconds, 1800)
        self.assertEqual(active.resource_name, 'normalization.pdf')
        page = self.client.get(reverse('study:study_dashboard'))
        self.assertContains(page, 'Databases')
        self.assertContains(page, 'normalization.pdf')

    def test_saving_active_session_moves_actual_time_to_history(self):
        active = ActiveStudySession.objects.create(
            user=self.user, subject=self.subject, planned_minutes=25,
            remaining_seconds=1320, notes='Read chapter one.', resource_name='chapter-1.pdf',
        )
        response = self.client.post(reverse('study:active_session_save'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ActiveStudySession.objects.filter(pk=active.pk).exists())
        saved = StudySession.objects.get(user=self.user)
        self.assertEqual(saved.planned_minutes, 25)
        self.assertEqual(saved.actual_seconds, 180)
        self.assertEqual(saved.duration_minutes, 3)
        self.assertEqual(saved.resource_name, 'chapter-1.pdf')
