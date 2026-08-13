from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Habit(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
    ]
    
    CATEGORY_CHOICES = [
        ('health', 'Health & Wellness'),
        ('fitness', 'Fitness & Exercise'),
        ('study', 'Study & Learning'),
        ('work', 'Work & Career'),
        ('personal', 'Personal Development'),
        ('mindfulness', 'Mindfulness & Meditation'),
        ('creative', 'Creative Hobbies'),
        ('social', 'Social & Relationships'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    icon = models.CharField(max_length=20, blank=True)  # Auto-filled based on category
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='DAILY')
    target_days = models.JSONField(default=list, blank=True)

    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-assign icon based on category
        icon_map = {
            'health': 'bi-heart-fill',
            'fitness': 'bi-lightning-fill',
            'study': 'bi-book-fill',
            'work': 'bi-briefcase-fill',
            'personal': 'bi-person-fill',
            'mindfulness': 'bi-yin-yang',
            'creative': 'bi-palette-fill',
            'social': 'bi-people-fill',
            'other': 'bi-star-fill',
        }
        if self.category and not self.icon:
            self.icon = icon_map.get(self.category, 'bi-star-fill')
        super().save(*args, **kwargs)

    def completion_rate(self):
        created_date = self.created_at.date()
        today = timezone.now().date()
        days_since_created = (today - created_date).days + 1
        
        if days_since_created <= 0:
            return 0
            
        completed_days = self.logs.filter(completed=True).count()
        return round((completed_days / days_since_created) * 100, 1)


class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField()
    completed = models.BooleanField(default=True)
    xp_awarded = models.BooleanField(default=False)

    class Meta:
        unique_together = ('habit', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.habit.name} - {self.date}"