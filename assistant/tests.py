from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import AIQueryLog
from .utils import MAX_QUERIES, build_user_context
from tasks.models import Task


class AssistantTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='assistant-user', password='password')
        self.client.login(username='assistant-user', password='password')

    def test_assistant_page_shows_daily_usage(self):
        AIQueryLog.objects.create(user=self.user, query='Plan my day', response='Start with your tasks.')
        response = self.client.get(reverse('assistant:assistant_page'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Today at a glance')
        self.assertContains(response, 'Messages today')
        self.assertContains(response, 'Plan my day')
        self.assertContains(response, 'Start with your tasks.')

    def test_assistant_page_only_shows_current_day_history(self):
        today_log = AIQueryLog.objects.create(user=self.user, query='Today question', response='Today answer')
        old_log = AIQueryLog.objects.create(user=self.user, query='Yesterday question', response='Yesterday answer')
        AIQueryLog.objects.filter(pk=old_log.pk).update(created_at=timezone.now() - timedelta(days=1))

        response = self.client.get(reverse('assistant:assistant_page'))

        self.assertContains(response, today_log.query)
        self.assertNotContains(response, old_log.query)

    def test_api_rejects_requests_after_daily_limit(self):
        AIQueryLog.objects.bulk_create([
            AIQueryLog(user=self.user, query=f'Question {number}', response='Answer')
            for number in range(MAX_QUERIES)
        ])
        response = self.client.post('/api/assistant/ask/', data='{"question":"Plan my tasks"}', content_type='application/json')

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()['usage'], MAX_QUERIES)

    def test_context_includes_task_content_for_current_user_only(self):
        Task.objects.create(user=self.user, title='Learn Django', description='Build a small blog app', priority='HIGH')
        another_user = User.objects.create_user(username='other-user', password='password')
        Task.objects.create(user=another_user, title='Private project', description='Do not expose this')

        context = build_user_context(self.user, 'How can I complete Learn Django?')

        self.assertIn('Learn Django', context)
        self.assertIn('Build a small blog app', context)
        self.assertNotIn('Private project', context)
        self.assertNotIn('Do not expose this', context)
