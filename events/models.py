from django.db import models
from django.conf import settings
from django.utils import timezone

from accounts.models import CustomUser


class EventCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # Font Awesome icon class
    
    def __str__(self):
        return self.name


class Event(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private')
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_events')
    category = models.ForeignKey(EventCategory, on_delete=models.SET_NULL, null=True)
    
    # Event details
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=200)
    location_details = models.TextField(blank=True)
    max_attendees = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Event settings
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    theme = models.CharField(max_length=100, blank=True)
    rules = models.TextField(blank=True)
    
    # Media
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return self.title

    @property
    def is_upcoming(self):
        return self.start_time > timezone.now()

    @property
    def attendee_count(self):
        return self.attendees.filter(status='accepted').count()

    @property
    def available_spots(self):
        return self.max_attendees - self.attendee_count
    
    @property
    def chat(self):
        """Get or create chat for this event"""
        from .models import EventChat
        chat, created = EventChat.objects.get_or_create(event=self)
        return chat


class EventAttendee(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendees')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    joined_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)  # Optional message when requesting to join

    class Meta:
        unique_together = ['event', 'user']

    def __str__(self):
        return f"{self.user.username} - {self.event.title}"


class EventInvitation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_invitations')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ['event', 'invitee']

    def __str__(self):
        return f"Invitation to {self.event.title} for {self.invitee.username}"

