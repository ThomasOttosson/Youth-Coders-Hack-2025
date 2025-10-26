# chat/urls.py
from django.urls import path
from . import views

# app_name = 'chat'

urlpatterns = [
    # Chat rooms list
    path('', views.chat_rooms, name='chat_rooms'),
    
    # Specific chat room
    path('room/<int:room_id>/', views.chat_room, name='chat_room'),
    
    # Message actions
    path('room/<int:room_id>/send/', views.send_message, name='send_message'),
    path('room/<int:room_id>/messages/', views.get_messages, name='get_messages'),
    path('room/<int:room_id>/mark-read/', views.mark_messages_read, name='mark_messages_read'),
    
    # Starting chats
    path('direct/<int:user_id>/', views.start_direct_message, name='start_direct_message'),
    path('event/<int:event_id>/', views.start_event_chat, name='start_event_chat'),
    path('group/create/', views.create_group_chat, name='create_group_chat'),
    
    # Management
    path('room/<int:room_id>/delete/', views.delete_chat_room, name='delete_chat_room'),
]