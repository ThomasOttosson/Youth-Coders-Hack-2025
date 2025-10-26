# chat/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('event', 'Event Chat'),
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
    ]
    
    name = models.CharField(max_length=100, blank=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, null=True, blank=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chat_rooms'  # This should already be here
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.room_type == 'event' and self.event:
            return f"Event Chat: {self.event.title}"
        elif self.room_type == 'direct':
            participants = self.participants.all()
            if participants.count() == 2:
                other_user = participants.exclude(id=self.creator.id).first() if hasattr(self, 'creator') else participants.first()
                return f"DM: {other_user.username}" if other_user else "Direct Message"
        return self.name or f"Chat Room {self.id}"
    
    def get_other_participant(self, user=None):
        """For direct messages, get the other participant"""
        print(f"{self.room_type} with participants: {[p.username for p in self.participants.all()]}")
        if self.room_type == 'direct' and self.participants.count() == 2:
            print(f"Getting other participant for room {self.id}")
            if user:
                return self.participants.exclude(id=user.id).first()
            # If no user provided, try to get from thread-local storage
            from django.contrib.auth import get_user
            print(f"Get user {get_user(None)} from thread-local storage")
            try:
                current_user = get_user(None)
                print(f"Current user in get_other_participant: {current_user}")
                if current_user and current_user.is_authenticated:
                    return self.participants.exclude(id=current_user.id).first()
            except:
                pass
        print("No other participant found or not a direct message room.")
        return None
    
    def get_last_message(self):
        """Get the most recent message in the room"""
        return self.messages.last()
    
    def get_other_participant_user(self):
        """Get the other participant for the current user (for template use)"""
        # This will be called in template context where we don't have access to request.user
        # We'll need to handle this differently in the view
        # if self.room_type == 'direct' and self.participants.count() == 2:
        #     return self.participants.exclude(id=user.id).first()
        return None

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username} in {self.room}"
    
    def mark_as_read(self):
        """Mark message as read"""
        self.is_read = True
        self.save()
