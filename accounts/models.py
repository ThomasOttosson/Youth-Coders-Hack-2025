from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField


class CustomUser(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = CloudinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.username

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    interests = models.ManyToManyField('events.EventCategory', blank=True)
    friends = models.ManyToManyField('self', symmetrical=True, blank=True)
    is_public = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class Friendship(models.Model):
    FRIEND_STATUS = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('blocked', 'Blocked'),
    ]
    
    from_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friendship_requests_sent')
    to_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friendship_requests_received')
    status = models.CharField(max_length=20, choices=FRIEND_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['from_user', 'to_user']
        verbose_name_plural = 'Friendships'

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"

    @classmethod
    def get_friends(cls, user):
        """Get all accepted friends for a user"""
        sent_friends = cls.objects.filter(
            from_user=user, 
            status='accepted'
        ).values_list('to_user', flat=True)
        
        received_friends = cls.objects.filter(
            to_user=user, 
            status='accepted'
        ).values_list('from_user', flat=True)
        
        friend_ids = list(sent_friends) + list(received_friends)
        return CustomUser.objects.filter(id__in=friend_ids)

    @classmethod
    def are_friends(cls, user1, user2):
        """Check if two users are friends"""
        return cls.objects.filter(
            (
                models.Q(from_user=user1, to_user=user2) |
                models.Q(from_user=user2, to_user=user1)
            ),
            status='accepted'
        ).exists()

    @classmethod
    def get_friend_count(cls, user):
        """Get the number of friends a user has"""
        return cls.objects.filter(
            (
                models.Q(from_user=user) |
                models.Q(to_user=user)
            ),
            status='accepted'
        ).count()

