from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('profile/deactivate/', views.deactivate_account, name='deactivate_account'),
    
    path('friends/', views.friend_list, name='friend_list'),
    path('friends/find/', views.find_friends, name='find_friends'),
    path('friends/suggestions/', views.friend_suggestions, name='friend_suggestions'),
    path('friends/add/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friends/accept/<int:friendship_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('friends/decline/<int:friendship_id>/', views.decline_friend_request, name='decline_friend_request'),
    path('friends/cancel/<int:friendship_id>/', views.cancel_friend_request, name='cancel_friend_request'),
    path('friends/remove/<int:friendship_id>/', views.remove_friend, name='remove_friend'),
    path('friends/block/<int:user_id>/', views.block_user, name='block_user'),
    path('friends/unblock/<int:friendship_id>/', views.unblock_user, name='unblock_user'),
    path('friends/mutual/<int:user_id>/', views.mutual_friends, name='mutual_friends'),
]
