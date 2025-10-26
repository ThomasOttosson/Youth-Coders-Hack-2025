# chat/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Count, Max
from django.contrib import messages
from django.core.paginator import Paginator
from .models import ChatRoom, Message
from .forms import MessageForm, DirectMessageForm, GroupChatForm
from events.models import Event, EventAttendee
from accounts.models import CustomUser, Friendship

@login_required
def chat_rooms(request):
    """Display all chat rooms for the user"""
    # Get user's chat rooms using the correct related name
    chat_rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_active=True
    ).prefetch_related('participants', 'messages').annotate(
        last_message_time=Max('messages__timestamp'),
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).order_by('-last_message_time')
    
    # In chat/views.py, update this line in chat_rooms view:
    user_events = Event.objects.filter(
        attendees__user=request.user,
        attendees__status='accepted'
    ).exclude(
        # Fix this line - use the correct related name from Event to ChatRoom
        id__in=ChatRoom.objects.filter(
            room_type='event',
            participants=request.user
        ).values_list('event_id', flat=True)
    )

    # Get friends for direct messaging
    friends = Friendship.get_friends(request.user)

    context = {
        'chat_rooms': chat_rooms,  # This is the queryset, not a related manager
        'user_events': user_events,
        'friends': friends,
    }
    
    return render(request, 'chat/chat_rooms.html', context)


@login_required
def chat_room(request, room_id):
    """Display a specific chat room"""
    room = get_object_or_404(
        ChatRoom.objects.prefetch_related('participants', 'messages__sender'),
        id=room_id,
        participants=request.user,
        is_active=True
    )
    print("Room Type:", room.room_type)
    print("Participants:", list(room.participants.all()))
    print("Current User:", request.user)
    
    if room.room_type == 'direct':
        other_user = room.get_other_participant(request.user)
        print("Other User:", other_user)
        if other_user:
            print("Other User Username:", other_user.username)
            
    # Mark messages as read
    room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    
    # Get messages with pagination
    messages_list = room.messages.all().select_related('sender')
    paginator = Paginator(messages_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all chat rooms for sidebar
    all_chat_rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_active=True
    ).prefetch_related('participants').annotate(
        last_message_time=Max('messages__timestamp')
    ).order_by('-last_message_time')
    
    form = MessageForm()
    
    context = {
        'room': room,
        'page_obj': page_obj,
        'form': form,
        'all_chat_rooms': all_chat_rooms,  # Add this for sidebar
        'current_room': room,  # Add this to highlight current room
        "other_user": other_user if room.room_type == 'direct' else None,
    }
    
    return render(request, 'chat/chat_room.html', context)


@login_required
def send_message(request, room_id):
    """Send a message in a chat room"""
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user, is_active=True)
        form = MessageForm(request.POST)
        
        if form.is_valid():
            message = form.save(commit=False)
            message.room = room
            message.sender = request.user
            message.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'sender': message.sender.username,
                        'sender_avatar_url': message.sender.avatar.url if message.sender.avatar else '/static/images/default-avatar.png',
                        'timestamp': message.timestamp.strftime('%b %d, %Y %I:%M %p'),
                        'is_read': message.is_read,
                    }
                })
            else:
                messages.success(request, 'Message sent!')
                return redirect('chat_room', room_id=room.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
            else:
                messages.error(request, 'Error sending message.')
    
    return redirect('chat_room', room_id=room_id)

@login_required
def start_direct_message(request, user_id):
    """Start or get existing direct message with a user"""
    other_user = get_object_or_404(CustomUser, id=user_id)
    
    if other_user == request.user:
        messages.error(request, "You cannot message yourself.")
        return redirect('chat_rooms')
    
    # Check if direct message room already exists
    existing_room = ChatRoom.objects.filter(
        room_type='direct',
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if existing_room:
        return redirect('chat_room', room_id=existing_room.id)
    
    # Create new direct message room
    room = ChatRoom.objects.create(room_type='direct')
    room.participants.add(request.user, other_user)
    room.save()
    
    messages.success(request, f"Started conversation with {other_user.username}")
    return redirect('chat_room', room_id=room.id)

@login_required
def start_event_chat(request, event_id):
    """Start or join event chat"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is attending the event
    is_attending = EventAttendee.objects.filter(
        event=event,
        user=request.user,
        status='accepted'
    ).exists()
    
    if not is_attending and request.user != event.host:
        messages.error(request, "You must be attending this event to join its chat.")
        return redirect('event_detail', event_id=event.id)
    
    # Check if event chat already exists
    existing_room = ChatRoom.objects.filter(
        room_type='event',
        event=event
    ).first()
    
    if existing_room:
        # Add user to participants if not already there
        if not existing_room.participants.filter(id=request.user.id).exists():
            existing_room.participants.add(request.user)
        return redirect('chat_room', room_id=existing_room.id)
    
    # Create new event chat
    room = ChatRoom.objects.create(
        room_type='event',
        event=event,
        name=f"Event Chat: {event.title}"
    )
    # Add event host and current user
    room.participants.add(event.host, request.user)
    # Add other attendees
    attendees = EventAttendee.objects.filter(event=event, status='accepted').select_related('user')
    for attendee in attendees:
        room.participants.add(attendee.user)
    
    room.save()
    
    messages.success(request, f"Joined chat for {event.title}")
    return redirect('chat_room', room_id=room.id)

@login_required
def create_group_chat(request):
    """Create a new group chat"""
    if request.method == 'POST':
        form = GroupChatForm(request.POST, user=request.user)
        if form.is_valid():
            room = form.save(commit=False)
            room.room_type = 'group'
            room.save()
            form.save_m2m()  # Save participants
            # Add creator as participant
            room.participants.add(request.user)
            room.save()
            
            messages.success(request, f"Group chat '{room.name}' created!")
            return redirect('chat_room', room_id=room.id)
    else:
        form = GroupChatForm(user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'chat/create_group_chat.html', context)

@login_required
def get_messages(request, room_id):
    """API endpoint to get messages for a room (for AJAX)"""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user, is_active=True)
    
    # Get messages after a specific ID (for polling)
    last_message_id = request.GET.get('last_message_id', 0)
    
    messages = room.messages.filter(
        id__gt=last_message_id
    ).select_related('sender').order_by('timestamp')
    
    messages_data = []
    for message in messages:
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'sender': {
                'username': message.sender.username,
                'avatar_url': message.sender.avatar.url if message.sender.avatar else '/static/images/default-avatar.png',
            },
            'timestamp': message.timestamp.strftime('%b %d, %Y %I:%M %p'),
            'is_read': message.is_read,
            'is_own_message': message.sender == request.user,
        })
    
    return JsonResponse({'messages': messages_data})

@login_required
def mark_messages_read(request, room_id):
    """Mark all messages in a room as read"""
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@login_required
def delete_chat_room(request, room_id):
    """Leave a chat room (soft delete for user)"""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    if request.method == 'POST':
        room.participants.remove(request.user)
        
        # If no participants left, deactivate the room
        if room.participants.count() == 0:
            room.is_active = False
            room.save()
        
        messages.success(request, "You have left the chat.")
        return redirect('chat_rooms')
    
    context = {
        'room': room,
    }
    return render(request, 'chat/delete_chat_room.html', context)
