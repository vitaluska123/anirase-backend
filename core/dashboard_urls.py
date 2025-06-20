# dashboard/urls.py
from django.urls import path
from .views.dashboard import *

dashboard_urlpatterns = [
    # Аутентификация для dashboard
    path('dashboard/login/', dashboard_login, name='dashboard_login'),
    
    # Основные данные dashboard
    path('dashboard/stats/', dashboard_stats, name='dashboard_stats'),
    path('dashboard/analytics/', dashboard_analytics, name='dashboard_analytics'),
    path('dashboard/activity/', dashboard_activity_full, name='dashboard_activity_full'),    # Управление пользователями
    path('dashboard/users/', dashboard_users, name='dashboard_users'),
    path('dashboard/users/create/', dashboard_user_create, name='dashboard_user_create'),
    path('dashboard/users/<int:user_id>/edit/', dashboard_user_edit, name='dashboard_user_edit'),
    path('dashboard/users/<int:user_id>/toggle-active/', dashboard_user_toggle_active, name='dashboard_user_toggle_active'),
    path('dashboard/users/<int:user_id>/delete/', dashboard_user_delete, name='dashboard_user_delete'),
    
    # Управление контентом
    path('dashboard/content/', dashboard_content, name='dashboard_content'),
    path('dashboard/comments/', dashboard_comments, name='dashboard_comments'),
    path('dashboard/comments/<int:comment_id>/delete/', dashboard_comment_delete, name='dashboard_comment_delete'),    path('dashboard/news/', dashboard_news, name='dashboard_news'),
    path('dashboard/news/create/', dashboard_news_create, name='dashboard_news_create'),
    path('dashboard/news/<int:news_id>/', dashboard_news_detail, name='dashboard_news_detail'),
    path('dashboard/news/<int:news_id>/edit/', dashboard_news_edit, name='dashboard_news_edit'),
    path('dashboard/news/<int:news_id>/toggle-published/', dashboard_news_toggle_published, name='dashboard_news_toggle_published'),
    path('dashboard/news/<int:news_id>/delete/', dashboard_news_delete, name='dashboard_news_delete'),
      # Управление комнатами
    path('dashboard/rooms/', dashboard_rooms, name='dashboard_rooms'),
    path('dashboard/rooms/stats/', dashboard_rooms_stats, name='dashboard_rooms_stats'),
    path('dashboard/rooms/<int:room_id>/delete/', dashboard_room_delete, name='dashboard_room_delete'),
    path('dashboard/rooms/<int:room_id>/sessions/', dashboard_room_sessions, name='dashboard_room_sessions'),
    
    # Управление магазином
    path('dashboard/shop/', dashboard_shop, name='dashboard_shop'),
]
