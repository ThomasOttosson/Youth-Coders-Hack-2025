from django import forms
from .models import Event, EventCategory, EventInvitation, EventAttendee
from django.utils import timezone
from datetime import datetime, time
from accounts.models import CustomUser, Friendship

# forms.py
from django import forms
from django.utils import timezone
from datetime import datetime, time
from .models import Event


class EventForm(forms.ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        required=True
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category', 'location', 'location_details',
            'max_attendees', 'price', 'privacy', 'theme', 'rules', 'image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Give your event a catchy name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your event'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Where is the event happening?'}),
            'location_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional location details'}),
            'max_attendees': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'privacy': forms.RadioSelect(),
            'theme': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Beach, 80s, Masquerade'}),
            'rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any specific rules for your event?'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for date and time fields if instance exists
        if self.instance and self.instance.pk:
            self.fields['start_date'].initial = self.instance.start_time.date()
            self.fields['start_time'].initial = self.instance.start_time.time()
            if self.instance.end_time:
                self.fields['end_date'].initial = self.instance.end_time.date()
                self.fields['end_time'].initial = self.instance.end_time.time()
        else:
            # Set default values for new events
            tomorrow = timezone.now() + timezone.timedelta(days=1)
            self.fields['start_date'].initial = tomorrow.date()
            self.fields['start_time'].initial = time(18, 0)  # 6:00 PM
            self.fields['end_date'].initial = tomorrow.date()
            self.fields['end_time'].initial = time(22, 0)  # 10:00 PM

    def clean(self):
        cleaned_data = super().clean()
        
        # Get the raw date and time values
        start_date = cleaned_data.get('start_date')
        start_time = cleaned_data.get('start_time')
        end_date = cleaned_data.get('end_date')
        end_time = cleaned_data.get('end_time')

        # Validate that we have all required datetime components
        errors = {}
        
        if not start_date:
            errors['start_date'] = 'Start date is required.'
        if not start_time:
            errors['start_time'] = 'Start time is required.'
        if not end_date:
            errors['end_date'] = 'End date is required.'
        if not end_time:
            errors['end_time'] = 'End time is required.'
        
        if errors:
            for field, error in errors.items():
                self.add_error(field, error)
            return cleaned_data

        # Create datetime objects
        try:
            start_datetime = timezone.make_aware(datetime.combine(start_date, start_time))
            end_datetime = timezone.make_aware(datetime.combine(end_date, end_time))
        except Exception as e:
            raise forms.ValidationError(f"Invalid date/time format: {str(e)}")

        # Store the combined datetime objects in cleaned_data so they're available in save()
        cleaned_data['start_datetime'] = start_datetime
        cleaned_data['end_datetime'] = end_datetime

        # Validate that event is in the future
        if start_datetime < timezone.now():
            self.add_error('start_date', 'Event must be in the future.')
            self.add_error('start_time', 'Event must be in the future.')

        # Validate that end time is after start time
        if end_datetime <= start_datetime:
            self.add_error('end_time', 'End time must be after start time.')

        return cleaned_data

    def save(self, commit=True):
        # Get the instance but don't save yet
        event = super().save(commit=False)
        
        # Set the datetime values from cleaned_data
        if 'start_datetime' in self.cleaned_data:
            event.start_time = self.cleaned_data['start_datetime']
        
        if 'end_datetime' in self.cleaned_data:
            event.end_time = self.cleaned_data['end_datetime']

        # Note: We don't set the host here anymore - it will be set in the view

        if commit:
            event.save()
            # Save many-to-many relationships if any
            self.save_m2m()

        return event

    
# forms.py
class EventInvitationForm(forms.ModelForm):
    invitees = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=True,
        label="Select friends to invite"
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add a personal message (optional)'
        }),
        label="Personal Message"
    )

    class Meta:
        model = EventInvitation
        fields = ['invitees', 'message']
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.inviter = kwargs.pop('inviter', None)
        super().__init__(*args, **kwargs)
        
        if self.inviter and self.event:
            # Get user's friends
            friends = Friendship.get_friends(self.inviter)
            
            # Exclude users who are already invited or attending
            already_invited = EventInvitation.objects.filter(
                event=self.event
            ).values_list('invitee', flat=True)
            
            already_attending = EventAttendee.objects.filter(
                event=self.event,
                status='accepted'
            ).values_list('user', flat=True)
            
            # Combine all excluded users
            excluded_users = set(already_invited) | set(already_attending) | {self.inviter.id}
            
            # Filter friends who can be invited
            available_friends = friends.exclude(id__in=excluded_users)
            
            self.fields['invitees'].queryset = available_friends
            
            # Add a helper text showing how many friends are available
            if available_friends.exists():
                self.fields['invitees'].help_text = f"Select from {available_friends.count()} available friends"
    
    def save(self, commit=True):
        invitations = []
        for invitee in self.cleaned_data['invitees']:
            invitation = EventInvitation(
                event=self.event,
                inviter=self.inviter,
                invitee=invitee,
                message=self.cleaned_data['message']
            )
            if commit:
                invitation.save()
            invitations.append(invitation)
        return invitations


class BulkInviteForm(forms.Form):
    emails = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter email addresses separated by commas or new lines'
        }),
        required=False,
        label="Email Addresses"
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add a personal message (optional)'
        }),
        label="Invitation Message"
    )

    def clean_emails(self):
        emails = self.cleaned_data['emails']
        if not emails:
            raise forms.ValidationError("Please enter at least one email address.")

        # Parse emails
        email_list = []
        for email in emails.replace(',', ' ').split():
            email = email.strip()
            if email:
                if not forms.EmailField().clean(email):
                    raise forms.ValidationError(f"'{email}' is not a valid email address.")
                email_list.append(email)

        if not email_list:
            raise forms.ValidationError("No valid email addresses found.")

        return email_list
