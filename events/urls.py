from django.urls import path
from . import views

urlpatterns = [
    path('', views.events_list, name='events_list'),
    path('my-events/', views.my_events, name='my_events'),
    path('create/', views.event_create, name='event_create'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('<int:event_id>/edit/', views.event_edit, name='event_edit'),
    path('<int:event_id>/manage/', views.event_manage, name='event_manage'),
    path('<int:event_id>/join/', views.event_join, name='event_join'),
    path('<int:event_id>/leave/', views.event_leave, name='event_leave'),
    path('attendee/<int:attendee_id>/<str:action>/', views.manage_attendee, name='manage_attendee'),
    path('event/<int:event_id>/delete/', views.event_delete_confirm, name='event_delete_confirm'),
    path('event/<int:event_id>/delete/confirm/', views.event_delete, name='event_delete'),
    path('event/<int:event_id>/cancel/', views.event_cancel, name='event_cancel'),
    path('<int:event_id>/invite/', views.event_invite, name='event_invite'),
    path('invitation/<int:invitation_id>/<str:action>/', views.manage_invitation, name='manage_invitation'),
    path('invitation/<int:invitation_id>/cancel/', views.cancel_invitation, name='cancel_invitation'),
    path('event/<int:event_id>/remove/<int:user_id>/', views.remove_attendee, name='remove_attendee'),
    path('event/<int:event_id>/approve/<int:user_id>/', views.approve_attendee, name='approve_attendee'),
    path('event/<int:event_id>/reject/<int:user_id>/', views.reject_attendee, name='reject_attendee'),
]