from django.urls import path
from . import api_views

urlpatterns = [
    path('analytics/task-completion/', api_views.TaskCompletionTrendAPIView.as_view(), name='api_task_completion'),
    path('analytics/habit-consistency/', api_views.HabitConsistencyAPIView.as_view(), name='api_habit_consistency'),
    path('analytics/study-breakdown/', api_views.StudyBreakdownAPIView.as_view(), name='api_study_breakdown'),
    path('analytics/focus-trend/', api_views.FocusTimeTrendAPIView.as_view(), name='api_focus_trend'),
    path('analytics/goal-progress/', api_views.GoalProgressAPIView.as_view(), name='api_goal_progress'),
    path('dashboard-summary/', api_views.DashboardSummaryAPIView.as_view(), name='api_dashboard_summary'),
]