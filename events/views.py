from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Event, EventCategory, EventAttendee, EventInvitation
from accounts.models import CustomUser, Friendship
from .forms import EventForm, EventInvitationForm, BulkInviteForm
from datetime import datetime, timedelta

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def events_list(request):
    # Get filter parameters
    category = request.GET.get('category')
    date_filter = request.GET.get('date')
    price_filter = request.GET.get('price')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'start_time')
    
    # Start with all upcoming events
    events = Event.objects.filter(start_time__gte=timezone.now())
    
    # Apply filters
    if category and category != 'all':
        events = events.filter(category__name=category)
    
    if date_filter and date_filter != '':
        today = timezone.now().date()
        if date_filter == 'today':
            events = events.filter(start_time__date=today)
        elif date_filter == 'tomorrow':
            tomorrow = today + timedelta(days=1)
            events = events.filter(start_time__date=tomorrow)
        elif date_filter == 'weekend':
            # Get upcoming weekend
            days_until_saturday = (5 - today.weekday()) % 7
            saturday = today + timedelta(days=days_until_saturday)
            sunday = saturday + timedelta(days=1)
            events = events.filter(start_time__date__in=[saturday, sunday])
        elif date_filter == 'week':
            next_week = today + timedelta(days=7)
            events = events.filter(start_time__date__range=[today, next_week])
    
    if price_filter and price_filter != '':
        if price_filter == 'free':
            events = events.filter(price=0)
        elif price_filter == 'under_20':
            events = events.filter(price__lt=20)
        elif price_filter == '20_50':
            events = events.filter(price__range=[20, 50])
        elif price_filter == 'over_50':
            events = events.filter(price__gt=50)
    
    if search_query and search_query != '' and search_query != None:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(theme__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by == 'popular':
        events = events.annotate(num_attendees=Count('attendees')).order_by('-num_attendees')
    elif sort_by == 'latest':
        events = events.order_by('-created_at')
    elif sort_by == 'nearest':
        events = events.order_by('start_time')
    else:  # soonest (default)
        events = events.order_by('start_time')
    
    # Get categories for filter
    categories = EventCategory.objects.all()
    
    # Get trending events (events with most attendees in next 7 days)
    trending_events = Event.objects.filter(
        start_time__range=[timezone.now(), timezone.now() + timedelta(days=7)]
    ).annotate(
        attendees_count=Count('attendees')
    ).order_by('-attendees_count')[:3]

    context = {
        'events': events,
        'categories': categories,
        'trending_events': trending_events,
        'current_filters': {
            'category': category,
            'date': date_filter,
            'price': price_filter,
            'search': search_query,
            'sort': sort_by,
        }
    }
    
    return render(request, 'events/events_list.html', context)


def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is attending
    is_attending = False
    if request.user.is_authenticated:
        is_attending = EventAttendee.objects.filter(
            event=event,
            user=request.user,
            status='accepted'
        ).exists()

    # Get attendees
    attendees = event.attendees.filter(status='accepted').select_related('user')
    
    # Get pending requests (only show to host)
    pending_requests = None
    if request.user.is_authenticated and request.user == event.host:
        pending_requests = event.attendees.filter(status='pending').select_related('user')
    
    context = {
        'event': event,
        'is_attending': is_attending,
        'attendees': attendees,
        'pending_requests': pending_requests,
    }
    
    return render(request, 'events/event_detail.html', context)


@login_required
@require_POST
def send_chat_message(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user can chat (must be attending or host)
    is_attending = EventAttendee.objects.filter(
        event=event, 
        user=request.user, 
        status='accepted'
    ).exists()
    
    if not (is_attending or request.user == event.host):
        return JsonResponse({'error': 'You must be attending this event to chat'}, status=403)
    
    form = ChatMessageForm(request.POST, request.FILES)
    
    if form.is_valid():
        # Get or create chat
        chat, created = EventChat.objects.get_or_create(event=event)
        
        # Create message
        message = form.save(commit=False)
        message.chat = chat
        message.user = request.user
        
        # Handle file name for uploaded files
        if message.file:
            message.file_name = message.file.name
        
        message.save()
        
        # Return message data for AJAX
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'user': {
                    'username': message.user.username,
                    'avatar_url': message.user.avatar.url if message.user.avatar else '/static/images/default-avatar.png',
                },
                'content': message.content,
                'message_type': message.message_type,
                'image_url': message.image.url if message.image else None,
                'file_url': message.file.url if message.file else None,
                'file_name': message.file_name,
                'created_at': message.created_at.strftime('%b %d, %Y %I:%M %p'),
                'is_edited': message.is_edited,
            }
        })
    else:
        return JsonResponse({'error': 'Invalid message'}, status=400)

@login_required
def get_chat_messages(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user can access chat
    is_attending = EventAttendee.objects.filter(
        event=event, 
        user=request.user, 
        status='accepted'
    ).exists()
    
    if not (is_attending or request.user == event.host):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    chat = get_object_or_404(EventChat, event=event)
    
    # Get messages after a specific ID (for polling)
    last_message_id = request.GET.get('last_message_id', 0)
    
    messages = chat.messages.filter(
        id__gt=last_message_id
    ).select_related('user').prefetch_related('reactions')[:50]
    
    messages_data = []
    for message in messages:
        messages_data.append({
            'id': message.id,
            'user': {
                'username': message.user.username,
                'avatar_url': message.user.avatar.url if message.user.avatar else '/static/images/default-avatar.png',
            },
            'content': message.content,
            'message_type': message.message_type,
            'image_url': message.image.url if message.image else None,
            'file_url': message.file.url if message.file else None,
            'file_name': message.file_name,
            'created_at': message.created_at.strftime('%b %d, %Y %I:%M %p'),
            'is_edited': message.is_edited,
            'reactions': [
                {
                    'emoji': reaction.emoji,
                    'count': ChatReaction.objects.filter(message=message, emoji=reaction.emoji).count(),
                    'users': list(ChatReaction.objects.filter(
                        message=message, emoji=reaction.emoji
                    ).values_list('user__username', flat=True)[:3])
                }
                for reaction in message.reactions.distinct('emoji')
            ]
        })
    
    return JsonResponse({'messages': messages_data})

@login_required
@require_POST
def add_reaction(request, message_id):
    message = get_object_or_404(ChatMessage, id=message_id)
    
    # Check if user can react (must be attending or host)
    is_attending = EventAttendee.objects.filter(
        event=message.chat.event, 
        user=request.user, 
        status='accepted'
    ).exists()
    
    if not (is_attending or request.user == message.chat.event.host):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    emoji = request.POST.get('emoji')
    
    if not emoji:
        return JsonResponse({'error': 'Emoji required'}, status=400)
    
    # Remove existing reaction from this user for this message
    ChatReaction.objects.filter(message=message, user=request.user).delete()
    
    # Add new reaction
    reaction = ChatReaction.objects.create(
        message=message,
        user=request.user,
        emoji=emoji
    )
    
    return JsonResponse({
        'success': True,
        'reaction': {
            'emoji': emoji,
            'count': ChatReaction.objects.filter(message=message, emoji=emoji).count(),
            'users': list(ChatReaction.objects.filter(
                message=message, emoji=emoji
            ).values_list('user__username', flat=True)[:3])
        }
    })

@login_required
@require_POST
def delete_message(request, message_id):
    message = get_object_or_404(ChatMessage, id=message_id)
    
    # Only message owner or event host can delete
    if message.user != request.user and request.user != message.chat.event.host:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    message_id = message.id
    message.delete()
    
    return JsonResponse({'success': True, 'message_id': message_id})


@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.host = request.user
            event.save()
            messages.success(request, 'Event created successfully!')
            return redirect('event_detail', event_id=event.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm()
    
    return render(request, 'events/event_create.html', {'form': form})



# views.py
@login_required
def event_edit(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        
        # Add debug prints to see what's happening
        print("POST data:", request.POST)
        print("FILES:", request.FILES)
        
        if form.is_valid():
            try:
                # Set the host for the form (in case it's needed for new events)
                form._host = request.user
                
                updated_event = form.save()
                print("Event saved successfully!")
                messages.success(request, 'Event updated successfully!')
                return redirect('event_detail', event_id=updated_event.id)
                
            except Exception as e:
                print(f"Error saving event: {str(e)}")
                messages.error(request, f'Error saving event: {str(e)}')
        else:
            print("Form errors:", form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm(instance=event)
    
    context = {
        'form': form,
        'event': event,
    }
    return render(request, 'events/event_edit.html', context)

# views.py
@login_required
def my_events(request):
    user = request.user
    active_tab = request.GET.get('tab', 'upcoming')
    
    # Get current datetime for filtering
    now = timezone.now()
    
    # Base queryset for user's events (hosting or attending)
    user_events = Event.objects.filter(
        Q(host=user) | Q(attendees__user=user)
    ).distinct()
    
    # Filter based on active tab
    if active_tab == 'upcoming':
        events = user_events.filter(
            start_time__gte=now
        ).order_by('start_time')
        page_title = "My Upcoming Events"
        
    elif active_tab == 'past':
        events = user_events.filter(
            start_time__lt=now
        ).order_by('-start_time')
        page_title = "My Past Events"
        
    elif active_tab == 'hosting':
        events = Event.objects.filter(
            host=user
        ).order_by('-created_at')
        page_title = "Events I'm Hosting"
        
    elif active_tab == 'attending':
        events = user_events.filter(
            attendees__user=user,
            attendees__status='accepted'
        ).exclude(host=user).order_by('start_time')
        page_title = "Events I'm Attending"
        
    else:  # all events
        events = user_events.order_by('-start_time')
        page_title = "All My Events"
    
    # Use a different name for annotation to avoid conflict
    events = events.annotate(
        attendees_count=Count('attendees', filter=Q(attendees__status='accepted'))
    ).select_related('host').prefetch_related('attendees')
    
    # Get counts for all tabs
    event_counts = {
        'all': user_events.count(),
        'upcoming': user_events.filter(start_time__gte=now).count(),
        'past': user_events.filter(start_time__lt=now).count(),
        'hosting': Event.objects.filter(host=user).count(),
        'attending': user_events.filter(
            attendees__user=user, 
            attendees__status='accepted'
        ).exclude(host=user).count(),
    }
    
    # Pagination
    paginator = Paginator(events, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'active_tab': active_tab,
        'page_title': page_title,
        'event_counts': event_counts,
        'now': now,
    }
    
    return render(request, 'events/my_events.html', context)


@login_required
def event_manage(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    
    # Get attendees and pending requests
    attendees = event.attendees.filter(status='accepted').select_related('user')
    pending_requests = event.attendees.filter(status='pending').select_related('user')
    
    # Calculate stats
    attendee_count = attendees.count()
    capacity_percentage = (attendee_count / event.max_attendees) * 100 if event.max_attendees > 0 else 0
    
    context = {
        'event': event,
        'attendees': attendees,
        'pending_requests': pending_requests,
        'attendee_count': attendee_count,
        'capacity_percentage': capacity_percentage,
    }
    
    return render(request, 'events/event_manage.html', context)

@login_required
def event_join(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is already attending
    existing_attendee = EventAttendee.objects.filter(event=event, user=request.user).first()
    
    if existing_attendee:
        if existing_attendee.status == 'accepted':
            messages.info(request, 'You are already attending this event.')
        elif existing_attendee.status == 'pending':
            messages.info(request, 'Your request to join is pending approval.')
        else:  # rejected
            messages.info(request, 'Your previous request was declined.')
    else:
        # Create new attendee request
        EventAttendee.objects.create(
            event=event,
            user=request.user,
            status='pending' if event.privacy == 'private' else 'accepted'
        )
        
        if event.privacy == 'private':
            messages.success(request, 'Join request sent! The host will review your request.')
        else:
            messages.success(request, 'You have successfully joined the event!')

    return redirect('event_detail', event_id=event.id)

@login_required
def event_leave(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Remove attendee
    EventAttendee.objects.filter(event=event, user=request.user).delete()
    messages.success(request, 'You have left the event.')

    return redirect('event_detail', event_id=event.id)

@login_required
def manage_attendee(request, attendee_id, action):
    attendee = get_object_or_404(EventAttendee, id=attendee_id)

    # Check if current user is the event host
    if request.user != attendee.event.host:
        messages.error(request, 'You do not have permission to manage this event.')
        return redirect('event_detail', event_id=attendee.event.id)

    if action == 'accept':
        attendee.status = 'accepted'
        attendee.save()
        messages.success(request, f'Request from {attendee.user.username} has been accepted.')
    elif action == 'reject':
        attendee.status = 'rejected'
        attendee.save()
        messages.info(request, f'Request from {attendee.user.username} has been declined.')

    return redirect('event_manage', event_id=attendee.event.id)


# views.py
@login_required
def event_invite(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user can invite (host or attendee for public events)
    can_invite = (
        request.user == event.host or 
        (event.privacy == 'public' and EventAttendee.objects.filter(
            event=event, user=request.user, status='accepted'
        ).exists())
    )
    
    if not can_invite:
        messages.error(request, "You don't have permission to invite people to this event.")
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'friends')
        
        if form_type == 'friends':
            form = EventInvitationForm(request.POST, event=event, inviter=request.user)
            if form.is_valid():
                try:
                    invitations = form.save()
                    messages.success(request, f'Invitations sent to {len(invitations)} friends!')
                    return redirect('event_invite', event_id=event.id)  # Stay on same page
                except Exception as e:
                    messages.error(request, f'Error sending invitations: {str(e)}')
        
        elif form_type == 'emails':
            email_form = BulkInviteForm(request.POST)
            if email_form.is_valid():
                emails = email_form.cleaned_data['emails']
                message = email_form.cleaned_data['message']
                
                # Send email invitations (implement this function)
                sent_count = send_email_invitations(event, request.user, emails, message)
                messages.success(request, f'Invitation emails sent to {sent_count} people!')
                
                return redirect('event_invite', event_id=event.id)
        else:
            messages.error(request, 'Invalid form submission.')
    else:
        form = EventInvitationForm(event=event, inviter=request.user)
        email_form = BulkInviteForm()
    
    # Get pending invitations for this event
    pending_invitations = EventInvitation.objects.filter(
        event=event, 
        is_accepted=False
    ).select_related('invitee')
    
    # Debug information (you can remove this later)
    if form.fields['invitees'].queryset.count() == 0:
        print(f"Debug: No friends available for user {request.user}")
        print(f"Debug: User's friends: {Friendship.get_friends(request.user).count()}")
        print(f"Debug: Already invited: {EventInvitation.objects.filter(event=event).count()}")
        print(f"Debug: Already attending: {EventAttendee.objects.filter(event=event, status='accepted').count()}")
    
    context = {
        'event': event,
        'form': form,
        'email_form': email_form,
        'pending_invitations': pending_invitations,
    }
    
    return render(request, 'events/event_invite.html', context)

@login_required
def manage_invitation(request, invitation_id, action):
    invitation = get_object_or_404(EventInvitation, id=invitation_id, invitee=request.user)
    
    if action == 'accept':
        invitation.status = 'accepted'
        invitation.save()
        
        # Auto-join the event
        EventAttendee.objects.get_or_create(
            event=invitation.event,
            user=request.user,
            defaults={'status': 'accepted'}
        )
        
        messages.success(request, f"You've accepted the invitation to {invitation.event.title}!")
        
    elif action == 'decline':
        invitation.status = 'declined'
        invitation.save()
        messages.info(request, f"You've declined the invitation to {invitation.event.title}.")
    
    return redirect('event_detail', event_id=invitation.event.id)

@login_required
def cancel_invitation(request, invitation_id):
    invitation = get_object_or_404(EventInvitation, id=invitation_id)
    
    # Check if user can cancel this invitation
    if request.user != invitation.inviter and request.user != invitation.event.host:
        messages.error(request, "You don't have permission to cancel this invitation.")
        return redirect('event_invite', event_id=invitation.event.id)
    
    invitation.delete()
    messages.success(request, "Invitation cancelled successfully.")
    
    return redirect('event_invite', event_id=invitation.event.id)

# Helper functions
def send_email_invitations(event, inviter, emails, message):
    sent_count = 0
    subject = f"You're invited to {event.title} on HAHA!"
    
    for email in emails:
        try:
            # Create invitation record
            try:
                invitee = CustomUser.objects.get(email=email)
                invitation = EventInvitation.objects.create(
                    event=event,
                    inviter=inviter,
                    invitee=invitee,
                    message=message
                )
            except CustomUser.DoesNotExist:
                # User doesn't exist in system, send email invitation to join
                invitation = None
            
            # Prepare email content
            context = {
                'event': event,
                'inviter': inviter,
                'message': message,
                'invitation': invitation,
            }
            
            html_message = render_to_string('events/email/invitation_email.html', context)
            plain_message = strip_tags(html_message)
            
            # Send email (configure email settings in your Django settings)
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=None,  # Use DEFAULT_FROM_EMAIL from settings
                recipient_list=[email],
                html_message=html_message,
                fail_silently=True,
            )
            
            sent_count += 1
            
        except Exception as e:
            print(f"Failed to send email to {email}: {e}")
            continue
    
    return sent_count

def send_invitation_notifications(invitations):
    # This would send in-app notifications
    # You can integrate with Django's messaging system or create a Notification model
    for invitation in invitations:
        # Create notification for invitee
        print(f"Notification: {invitation.invitee.username} was invited to {invitation.event.title}")
        # You can implement actual notification logic here


@login_required
@require_POST
def event_delete(request, event_id):
    """Delete an event (only by host)"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the host
    if event.host != request.user:
        messages.error(request, "You don't have permission to delete this event.")
        return redirect('event_detail', event_id=event.id)
    
    # Optional: Check if event has already started
    if event.start_time <= timezone.now():
        messages.warning(request, "Cannot delete events that have already started.")
        return redirect('event_detail', event_id=event.id)
    
    event_title = event.title
    event_id = event.id
    
    try:
        event.delete()
        messages.success(request, f'Event "{event_title}" has been deleted successfully.')
        
        # Redirect to my_events page after deletion
        return redirect('my_events')
        
    except Exception as e:
        messages.error(request, f'Error deleting event: {str(e)}')
        return redirect('event_detail', event_id=event_id)

@login_required
def event_delete_confirm(request, event_id):
    """Confirmation page for event deletion"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the host
    if event.host != request.user:
        messages.error(request, "You don't have permission to delete this event.")
        return redirect('event_detail', event_id=event.id)
    
    # Check if event has already started
    if event.start_time <= timezone.now():
        messages.warning(request, "Cannot delete events that have already started.")
        return redirect('event_detail', event_id=event.id)
    
    # Get attendee count for warning message
    attendee_count = event.attendees.filter(status='accepted').count()
    
    context = {
        'event': event,
        'attendee_count': attendee_count,
    }
    
    return render(request, 'events/event_delete_confirm.html', context)

@login_required
@require_POST
def event_cancel(request, event_id):
    """Cancel an event (soft delete for events that have started)"""
    event = get_object_or_404(Event, id=event_id)
    
    if event.host != request.user:
        messages.error(request, "You don't have permission to cancel this event.")
        return redirect('event_detail', event_id=event.id)
    
    event_title = event.title
    
    try:
        # Instead of deleting, mark as cancelled
        event.status = 'cancelled'  # Add this field to your Event model
        event.save()
        
        # Send notifications to attendees (you can implement this later)
        # send_event_cancellation_notifications(event)
        
        messages.warning(request, f'Event "{event_title}" has been cancelled.')
        return redirect('my_events')
        
    except Exception as e:
        messages.error(request, f'Error cancelling event: {str(e)}')
        return redirect('event_detail', event_id=event.id)

# views.py
@login_required
@require_POST
def remove_attendee(request, event_id, user_id):
    """Remove an attendee from the event"""
    event = get_object_or_404(Event, id=event_id, host=request.user)
    user = get_object_or_404(CustomUser, id=user_id)
    
    attendance = get_object_or_404(EventAttendee, event=event, user=user)
    
    try:
        attendance.delete()
        messages.success(request, f'{user.username} has been removed from the event.')
    except Exception as e:
        messages.error(request, f'Error removing attendee: {str(e)}')
    
    return redirect('event_manage', event_id=event.id)

@login_required
@require_POST
def approve_attendee(request, event_id, user_id):
    """Approve a pending attendance request"""
    event = get_object_or_404(Event, id=event_id, host=request.user)
    user = get_object_or_404(CustomUser, id=user_id)
    
    attendance = get_object_or_404(EventAttendee, event=event, user=user, status='pending')
    
    try:
        attendance.status = 'accepted'
        attendance.save()
        messages.success(request, f'{user.username} has been approved to attend the event.')
    except Exception as e:
        messages.error(request, f'Error approving attendee: {str(e)}')
    
    return redirect('event_manage', event_id=event.id)

@login_required
@require_POST
def reject_attendee(request, event_id, user_id):
    """Reject a pending attendance request"""
    event = get_object_or_404(Event, id=event_id, host=request.user)
    user = get_object_or_404(CustomUser, id=user_id)
    
    attendance = get_object_or_404(EventAttendee, event=event, user=user, status='pending')
    
    try:
        attendance.delete()
        messages.info(request, f'{user.username} has been rejected from the event.')
    except Exception as e:
        messages.error(request, f'Error rejecting attendee: {str(e)}')
    
    return redirect('event_manage', event_id=event.id)


