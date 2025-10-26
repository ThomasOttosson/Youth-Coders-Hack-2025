from django.shortcuts import render
from events.models import Event
from django.utils import timezone
from django.db.models import Count, Q

def home(request):
    try:
        # Get upcoming events with attendee count
        upcoming_events = Event.objects.with_attendee_count().filter(
            start_time__gte=timezone.now()
        ).order_by('start_time')[:6]

        # Get trending events using the manager method
        trending_events = Event.objects.trending(limit=3)
        
    except Exception:
        # Fallback in case of any database issues
        upcoming_events = Event.objects.filter(
            start_time__gte=timezone.now()
        ).order_by('start_time')[:6]
        trending_events = Event.objects.filter(
            start_time__gte=timezone.now()
        ).order_by('-created_at')[:3]

    context = {
        'upcoming_events': upcoming_events,
        'trending_events': trending_events,
    }
    return render(request, 'home.html', context)
