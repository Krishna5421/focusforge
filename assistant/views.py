from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def assistant_page(request):
    return render(request, 'assistant/assistant.html')