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
    
    # Управление магазином
    path('dashboard/shop/', dashboard_shop, name='dashboard_shop'),
]
