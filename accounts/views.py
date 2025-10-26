from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from .forms import CustomUserCreationForm, CustomAuthenticationForm, FriendSearchForm
from .models import CustomUser, Friendship
from events.models import Event
from django.utils import timezone
from django.db import transaction
from datetime import timedelta  # Add this import

from django.contrib.auth import get_user_model



def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to HAHA!')
            return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def profile_view(request, username):
    try:
        # Use the same user model that request.user uses
        user = get_user_model().objects.get(username=username)
        # Or if you know it's CustomUser, use it explicitly:
        # user = CustomUser.objects.get(username=username)
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('home')

    # Get friendship status
    is_friend = False
    friend_request_sent = False
    friend_request_received = False
    friendship_id = None
    mutual_count = 0
    
    if request.user != user:
        # Check friendship status
        friendship = Friendship.objects.filter(
            (Q(from_user=request.user, to_user=user) |
             Q(from_user=user, to_user=request.user))
        ).first()
        
        if friendship:
            friendship_id = friendship.id
            if friendship.status == 'accepted':
                is_friend = True
            elif friendship.status == 'pending':
                if friendship.from_user == request.user:
                    friend_request_sent = True
                else:
                    friend_request_received = True
        
        # Get mutual friends count
        user_friends = set(Friendship.get_friends(request.user))
        profile_friends = set(Friendship.get_friends(user))
        mutual_count = len(user_friends.intersection(profile_friends))

    # Get user's upcoming events
    upcoming_events = Event.objects.filter(
        Q(host=user) | Q(attendees__user=user, attendees__status='accepted'),
        start_time__gte=timezone.now()
    ).distinct().order_by('start_time')[:6]
    
    # Get friend count
    friend_count = len(Friendship.get_friends(user))
    
    # Get event count (hosted + attending)
    event_count = Event.objects.filter(
        Q(host=user) | Q(attendees__user=user, attendees__status='accepted')
    ).distinct().count()
    
    # Recent activity (simplified - you can expand this)
    recent_activity = [
        {
            'type': 'event_created',
            'description': f'Created event "Test Event"',
            'timestamp': timezone.now() - timedelta(hours=2)
        },
        {
            'type': 'friend_added',
            'description': f'Became friends with Another User',
            'timestamp': timezone.now() - timedelta(days=1)
        }
    ]
    
    context = {
        'profile_user': user,
        'is_friend': is_friend,
        'friend_request_sent': friend_request_sent,
        'friend_request_received': friend_request_received,
        'friendship_id': friendship_id,
        'mutual_count': mutual_count,
        'upcoming_events': upcoming_events,
        'friend_count': friend_count,
        'event_count': event_count,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    if request.method == 'POST':
        user = request.user
        
        # Update fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.bio = request.POST.get('bio', '')
        user.location = request.POST.get('location', '')
        user.phone = request.POST.get('phone', '')
        
        # Handle privacy settings
        user.profile_public = 'profile_public' in request.POST
        user.show_email = 'show_email' in request.POST
        user.event_notifications = 'event_notifications' in request.POST
        
        # Handle avatar upload
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
            
            # Always use request.user.username for redirect
            return redirect('profile', username=request.user.username)
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    # For both GET and POST errors, render the form
    return render(request, 'accounts/profile_edit.html', {'user': request.user})



# Add this temporary debug view
@login_required
def profile_edit_debug(request):
    if request.method == 'POST':
        user = request.user
        
        # Update fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.bio = request.POST.get('bio', '')
        user.location = request.POST.get('location', '')
        user.phone = request.POST.get('phone', '')
        
        # Handle privacy settings
        user.profile_public = 'profile_public' in request.POST
        user.show_email = 'show_email' in request.POST
        user.event_notifications = 'event_notifications' in request.POST
        
        # Handle avatar upload
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
            
            # Always use request.user.username for redirect
            return redirect('profile', username=request.user.username)
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    # For both GET and POST errors, render the form
    return render(request, 'accounts/profile_edit.html', {'user': request.user})



@login_required
def delete_account(request):
    if request.method == 'POST':
        # Verify username confirmation
        confirm_username = request.POST.get('confirm_username', '').strip()
        
        if confirm_username != request.user.username:
            messages.error(request, 'Username confirmation failed. Please type your username exactly.')
            return redirect('profile_edit')
        
        try:
            with transaction.atomic():
                user = request.user
                username = user.username
                email = user.email
                
                # Optional: Create a log of account deletion
                print(f"Account deletion requested for user: {username} ({email})")
                
                # If you want to soft delete instead of hard delete:
                # user.is_active = False
                # user.email = f"deleted_{user.id}@example.com"
                # user.username = f"deleted_user_{user.id}"
                # user.save()
                
                # Hard delete - permanently remove the user
                user.delete()
                
                # Log the user out
                logout(request)
                
                messages.success(request, 'Your account has been permanently deleted. We hope to see you again!')
                return redirect('home')
                
        except Exception as e:
            messages.error(request, f'An error occurred while deleting your account: {str(e)}')
            return redirect('profile_edit')
    
    # If GET request, show confirmation page
    return render(request, 'accounts/delete_account_confirm.html')

@login_required
def deactivate_account(request):
    """Soft delete option - deactivate instead of permanent deletion"""
    if request.method == 'POST':
        confirm_username = request.POST.get('confirm_username', '').strip()
        
        if confirm_username != request.user.username:
            messages.error(request, 'Username confirmation failed. Please type your username exactly.')
            return redirect('profile_edit')
        
        try:
            user = request.user
            user.is_active = False
            user.save()
            
            logout(request)
            
            messages.info(request, 'Your account has been deactivated. You can reactivate it by logging in again.')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'An error occurred while deactivating your account: {str(e)}')
            return redirect('profile_edit')
    
    return render(request, 'accounts/deactivate_account_confirm.html')


@login_required
def friend_list(request):
    """Display user's current friends"""
    friends = Friendship.get_friends(request.user)
    
    # Get pending friend requests
    pending_requests = Friendship.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user')
    
    # Get sent pending requests
    sent_requests = Friendship.objects.filter(
        from_user=request.user,
        status='pending'
    ).select_related('to_user')
    
    context = {
        'friends': friends,
        'pending_requests': pending_requests,
        'sent_requests': sent_requests,
        'active_tab': 'friends',
    }
    return render(request, 'accounts/friend_list.html', context)

@login_required
def find_friends(request):
    """Find and search for new friends"""
    users = CustomUser.objects.exclude(id=request.user.id)
    form = FriendSearchForm(request.GET or None)
    
    if form.is_valid():
        query = form.cleaned_data.get('query')
        if query:
            users = users.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
    
    # Exclude existing friends and pending requests
    existing_friendships = Friendship.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).values_list('from_user', 'to_user')
    
    excluded_users = set()
    for from_user, to_user in existing_friendships:
        if from_user == request.user.id:
            excluded_users.add(to_user)
        else:
            excluded_users.add(from_user)
    
    users = users.exclude(id__in=excluded_users)
    
    # Pagination
    paginator = Paginator(users, 12)  # 12 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'active_tab': 'find_friends',
        'query': request.GET.get('query', ''),
    }
    return render(request, 'accounts/find_friends.html', context)

@login_required
def send_friend_request(request, user_id):
    """Send a friend request to another user"""
    to_user = get_object_or_404(CustomUser, id=user_id)
    
    if to_user == request.user:
        messages.error(request, "You cannot send a friend request to yourself.")
        return redirect('find_friends')
    
    # Check if friendship already exists
    existing_friendship = Friendship.objects.filter(
        (Q(from_user=request.user, to_user=to_user) |
         Q(from_user=to_user, to_user=request.user))
    ).first()
    
    if existing_friendship:
        if existing_friendship.status == 'accepted':
            messages.info(request, f"You are already friends with {to_user.username}.")
        elif existing_friendship.status == 'pending':
            if existing_friendship.from_user == request.user:
                messages.info(request, f"Friend request to {to_user.username} is already pending.")
            else:
                messages.info(request, f"{to_user.username} has already sent you a friend request.")
        elif existing_friendship.status == 'blocked':
            messages.error(request, "This friendship has been blocked.")
        return redirect('find_friends')
    
    # Create new friend request
    friendship = Friendship.objects.create(
        from_user=request.user,
        to_user=to_user,
        status='pending'
    )
    
    messages.success(request, f"Friend request sent to {to_user.username}!")
    
    # Redirect back to previous page or find friends
    next_url = request.META.get('HTTP_REFERER', 'find_friends')
    return redirect(next_url)

@login_required
def accept_friend_request(request, friendship_id):
    """Accept a pending friend request"""
    friendship = get_object_or_404(Friendship, id=friendship_id, to_user=request.user, status='pending')
    
    friendship.status = 'accepted'
    friendship.save()
    
    messages.success(request, f"You are now friends with {friendship.from_user.username}!")
    
    # Redirect back to previous page or friend list
    next_url = request.META.get('HTTP_REFERER', 'friend_list')
    return redirect(next_url)

@login_required
def decline_friend_request(request, friendship_id):
    """Decline a pending friend request"""
    friendship = get_object_or_404(Friendship, id=friendship_id, to_user=request.user, status='pending')
    
    friendship.delete()
    
    messages.info(request, f"Friend request from {friendship.from_user.username} declined.")
    
    next_url = request.META.get('HTTP_REFERER', 'friend_list')
    return redirect(next_url)

@login_required
def cancel_friend_request(request, friendship_id):
    """Cancel a sent friend request"""
    friendship = get_object_or_404(Friendship, id=friendship_id, from_user=request.user, status='pending')
    
    friendship.delete()
    
    messages.info(request, f"Friend request to {friendship.to_user.username} cancelled.")
    
    next_url = request.META.get('HTTP_REFERER', 'friend_list')
    return redirect(next_url)

@login_required
def remove_friend(request, friendship_id):
    """Remove a friend (unfriend)"""
    friendship = get_object_or_404(Friendship, id=friendship_id)
    
    # Verify the user is part of this friendship
    if friendship.from_user != request.user and friendship.to_user != request.user:
        messages.error(request, "You don't have permission to remove this friendship.")
        return redirect('friend_list')
    
    friend_username = friendship.to_user.username if friendship.from_user == request.user else friendship.from_user.username
    
    friendship.delete()
    
    messages.info(request, f"You are no longer friends with {friend_username}.")
    
    next_url = request.META.get('HTTP_REFERER', 'friend_list')
    return redirect(next_url)

@login_required
def block_user(request, user_id):
    """Block a user"""
    user_to_block = get_object_or_404(CustomUser, id=user_id)
    
    if user_to_block == request.user:
        messages.error(request, "You cannot block yourself.")
        return redirect('find_friends')
    
    # Delete any existing friendship or create blocked relationship
    Friendship.objects.filter(
        (Q(from_user=request.user, to_user=user_to_block) |
         Q(from_user=user_to_block, to_user=request.user))
    ).delete()
    
    # Create blocked relationship
    Friendship.objects.create(
        from_user=request.user,
        to_user=user_to_block,
        status='blocked'
    )
    
    messages.warning(request, f"You have blocked {user_to_block.username}.")
    
    next_url = request.META.get('HTTP_REFERER', 'friend_list')
    return redirect(next_url)

@login_required
def unblock_user(request, friendship_id):
    """Unblock a user"""
    friendship = get_object_or_404(Friendship, id=friendship_id, from_user=request.user, status='blocked')
    
    blocked_username = friendship.to_user.username
    friendship.delete()
    
    messages.info(request, f"You have unblocked {blocked_username}.")
    
    next_url = request.META.get('HTTP_REFERER', 'friend_list')
    return redirect(next_url)

@login_required
def friend_suggestions(request):
    """Get friend suggestions based on common events and mutual friends"""
    # Get users who attended same events
    user_events = Event.objects.filter(
        Q(host=request.user) | 
        Q(attendees__user=request.user)
    ).distinct()
    
    suggested_users = CustomUser.objects.exclude(id=request.user.id)
    
    # Exclude existing friends and pending requests
    existing_friendships = Friendship.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).values_list('from_user', 'to_user')
    
    excluded_users = set()
    for from_user, to_user in existing_friendships:
        if from_user == request.user.id:
            excluded_users.add(to_user)
        else:
            excluded_users.add(from_user)
    
    suggested_users = suggested_users.exclude(id__in=excluded_users)
    
    # Find users who attended same events
    event_attendees = CustomUser.objects.filter(
        Q(hosted_events__in=user_events) |
        Q(events_attending__event__in=user_events)
    ).exclude(id=request.user.id).exclude(id__in=excluded_users).distinct()
    
    # Add mutual friends count annotation
    from django.db.models import Count, Subquery, OuterRef
    
    # This is a simplified version - you might want to optimize this
    suggested_users = suggested_users.annotate(
        common_events_count=Count(
            'hosted_events',
            filter=Q(hosted_events__in=user_events)
        ) + Count(
            'events_attending__event',
            filter=Q(events_attending__event__in=user_events)
        )
    ).order_by('-common_events_count')[:20]
    
    context = {
        'suggested_users': suggested_users,
        'active_tab': 'suggestions',
    }
    return render(request, 'accounts/friend_suggestions.html', context)

@login_required
def mutual_friends(request, user_id):
    """Show mutual friends between current user and another user"""
    other_user = get_object_or_404(CustomUser, id=user_id)
    
    # Get current user's friends
    current_user_friends = set(Friendship.get_friends(request.user))
    
    # Get other user's friends
    other_user_friends = set(Friendship.get_friends(other_user))
    
    # Find mutual friends
    mutual_friends = current_user_friends.intersection(other_user_friends)
    
    # Check friendship status
    friendship_status = None
    existing_friendship = Friendship.objects.filter(
        (Q(from_user=request.user, to_user=other_user) |
         Q(from_user=other_user, to_user=request.user))
    ).first()
    
    if existing_friendship:
        friendship_status = existing_friendship.status
    
    context = {
        'other_user': other_user,
        'mutual_friends': mutual_friends,
        'friendship_status': friendship_status,
        'mutual_count': len(mutual_friends),
    }
    return render(request, 'accounts/mutual_friends.html', context)
