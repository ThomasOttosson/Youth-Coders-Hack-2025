# chat/forms.py
from django import forms
from .models import Message, ChatRoom

class MessageForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Type your message...',
            'class': 'form-control message-input'
        }),
        label=''
    )
    
    class Meta:
        model = Message
        fields = ['content']

class DirectMessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Type your message...',
            'class': 'form-control message-input'
        }),
        label=''
    )
    recipient_id = forms.IntegerField(widget=forms.HiddenInput())

class GroupChatForm(forms.ModelForm):
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter group name'
        })
    )
    participants = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2'
        }),
        required=True
    )
    
    class Meta:
        model = ChatRoom
        fields = ['name', 'participants']
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Exclude current user from participant choices
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.fields['participants'].queryset = User.objects.exclude(id=user.id)
