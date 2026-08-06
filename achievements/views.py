from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import UserAchievement
from .utils import check_all_achievements


@login_required
def achievement_list(request):
    check_all_achievements(request.user)
    unlocked = UserAchievement.objects.filter(user=request.user)
    return render(request, 'achievements/achievement_list.html', {'unlocked': unlocked})