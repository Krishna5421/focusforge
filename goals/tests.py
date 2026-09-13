from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Goal, Milestone


class GoalAjaxTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='goal-user', password='pass12345')
        self.other_user = User.objects.create_user(username='other-user', password='pass12345')
        self.client.login(username='goal-user', password='pass12345')

    def test_ajax_create_saves_goal_and_milestones(self):
        response = self.client.post(reverse('goals:ajax_goal_create'), {
            'title': 'Launch project',
            'deadline': '2026-12-31',
            'milestones': 'Plan\nBuild\nLaunch',
        })
        self.assertEqual(response.status_code, 200)
        goal = Goal.objects.get(title='Launch project')
        self.assertEqual(goal.user, self.user)
        self.assertEqual(list(goal.milestones.values_list('title', flat=True)), ['Plan', 'Build', 'Launch'])

    def test_milestone_toggle_updates_goal_progress_and_status(self):
        goal = Goal.objects.create(user=self.user, title='Goal', deadline='2026-12-31')
        milestone = Milestone.objects.create(goal=goal, title='Only step')
        response = self.client.post(reverse('goals:ajax_milestone_toggle', args=[milestone.pk]))
        self.assertEqual(response.status_code, 200)
        goal.refresh_from_db()
        self.assertEqual(goal.completion_percentage, 100)
        self.assertEqual(goal.status, 'COMPLETED')

    def test_ajax_delete_cannot_delete_another_users_goal(self):
        goal = Goal.objects.create(user=self.user, title='Own', deadline='2026-12-31')
        other_goal = Goal.objects.create(user=self.other_user, title='Other', deadline='2026-12-31')
        response = self.client.post(reverse('goals:ajax_goal_delete', args=[goal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Goal.objects.filter(pk=goal.pk).exists())
        self.assertTrue(Goal.objects.filter(pk=other_goal.pk).exists())

# Create your tests here.
