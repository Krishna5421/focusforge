from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tasks.models import Task
from .models import Achievement, UserAchievement


class AchievementPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='achiever', password='password')
        self.client.login(username='achiever', password='password')
        self.first_task = Achievement.objects.create(
            name='First Task', icon='✓', criteria_type='TASKS_COMPLETED', criteria_value=1, xp_reward=20,
        )
        self.task_master = Achievement.objects.create(
            name='Task Master', icon='★', criteria_type='TASKS_COMPLETED', criteria_value=5, xp_reward=75,
        )

    def test_page_unlocks_and_shows_locked_task_progress(self):
        Task.objects.create(user=self.user, title='Done', status='COMPLETED')
        response = self.client.get(reverse('achievements:achievement_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserAchievement.objects.filter(user=self.user, achievement=self.first_task).exists())
        self.assertContains(response, 'First Task')
        self.assertContains(response, 'Task Master')
        self.assertContains(response, '4 more tasks to unlock')
        self.assertContains(response, 'XP to Level 2')
