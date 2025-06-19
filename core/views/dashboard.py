# dashboard/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import Count, Q
from datetime import datetime, timedelta
from core.models import *

def check_staff_permission(user):
    """
    Проверяет, является ли пользователь staff
    """
    if not user.is_authenticated:
        return False, {'error': 'Authentication required', 'message': 'Необходима аутентификация'}
    
    if not user.is_staff:
        return False, {'error': 'Access denied', 'message': 'Доступ к панели администратора разрешен только для сотрудников'}
    
    return True, None

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dashboard_login(request):
    """
    Специальный эндпоинт для логина в dashboard.
    Проверяет staff статус.
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    return Response({
        'success': True,
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Получение общей статистики для dashboard
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    # Общая статистика
    total_users = User.objects.count()
    try:
        total_news = News.objects.count()
    except:
        total_news = 0
    
    try:
        total_products = Product.objects.count()
    except:
        total_products = 0
    
    try:
        total_comments = Comment.objects.count()
    except:
        total_comments = 0
    
    # Статистика за последние 30 дней
    thirty_days_ago = datetime.now() - timedelta(days=30)
    new_users_month = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    
    # Активные пользователи (заходили за последние 7 дней)
    week_ago = datetime.now() - timedelta(days=7)
    active_users = User.objects.filter(last_login__gte=week_ago).count()
    
    return Response({
        'data': {
            'total_users': total_users,
            'total_news': total_news,
            'total_products': total_products,
            'total_comments': total_comments,
            'new_users_month': new_users_month,
            'active_users': active_users,
            'users_growth': round((new_users_month / max(total_users, 1)) * 100, 1),
            'online_users': active_users,  # Упрощение для примера
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_users(request):
    """
    Получение списка пользователей для управления
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    search = request.GET.get('search', '')
    
    users_query = User.objects.all()
    
    if search:
        users_query = users_query.filter(
            Q(username__icontains=search) | 
            Q(email__icontains=search)
        )
    
    total = users_query.count()
    users = users_query[(page-1)*limit:page*limit]
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None
        })
    
    return Response({
        'data': users_data,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': (total + limit - 1) // limit
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_content(request):
    """
    Получение статистики контента
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    # Статистика новостей
    try:
        news_count = News.objects.count()
        published_news = News.objects.filter(created_at__gte=datetime.now() - timedelta(days=30)).count()
    except:
        news_count = 0
        published_news = 0
    
    # Статистика комментариев
    try:
        comments_count = Comment.objects.count()
        recent_comments = Comment.objects.filter(created_at__gte=datetime.now() - timedelta(days=7)).count()
    except:
        comments_count = 0
        recent_comments = 0
    
    return Response({
        'data': {
            'news_total': news_count,
            'news_published_month': published_news,
            'comments_total': comments_count,
            'comments_recent': recent_comments
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_shop(request):
    """
    Получение статистики магазина
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    # Статистика продуктов
    try:
        products_count = Product.objects.count()
        categories_count = ProductCategory.objects.count()
    except:
        products_count = 0
        categories_count = 0
    
    # Статистика заказов (если есть модель Order)
    orders_count = 0  # Заглушка, так как модель Order может отсутствовать
    
    return Response({
        'data': {
            'products_total': products_count,
            'categories_total': categories_count,
            'orders_total': orders_count
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_analytics(request):
    """
    Получение аналитических данных
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    # Данные для графиков активности пользователей за последние 30 дней
    user_activity = []
    for i in range(30):
        date = datetime.now() - timedelta(days=29-i)
        day_users = User.objects.filter(date_joined__date=date.date()).count()
        user_activity.append({
            'name': date.strftime('%d.%m'),
            'value': day_users
        })
    
    # Данные по просмотрам контента по дням недели
    content_views = [
        {'name': 'Пн', 'value': 120},
        {'name': 'Вт', 'value': 98},
        {'name': 'Ср', 'value': 156},
        {'name': 'Чт', 'value': 134},
        {'name': 'Пт', 'value': 178},
        {'name': 'Сб', 'value': 203},
        {'name': 'Вс', 'value': 167}
    ]
      # Последняя активность - реальные данные
    recent_activities = []
    
    # Получаем последних зарегистрированных пользователей
    recent_users = User.objects.filter(
        date_joined__gte=datetime.now() - timedelta(days=7)
    ).order_by('-date_joined')[:3]
    
    for user in recent_users:
        time_diff = datetime.now() - user.date_joined.replace(tzinfo=None)
        if time_diff.days > 0:
            time_str = f"{time_diff.days} дн. назад"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_str = f"{hours} ч. назад"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            time_str = f"{minutes} мин. назад"
        else:
            time_str = "только что"
            
        recent_activities.append({
            'id': f"user_{user.id}",
            'type': 'user_register',
            'user': user.username,
            'action': 'зарегистрировался',
            'time': time_str
        })
    
    # Получаем последние комментарии
    try:
        recent_comments = Comment.objects.select_related('user').filter(
            created_at__gte=datetime.now() - timedelta(days=7)
        ).order_by('-created_at')[:5]
        
        for comment in recent_comments:
            time_diff = datetime.now() - comment.created_at.replace(tzinfo=None)
            if time_diff.days > 0:
                time_str = f"{time_diff.days} дн. назад"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours} ч. назад"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                time_str = f"{minutes} мин. назад"
            else:
                time_str = "только что"
                
            recent_activities.append({
                'id': f"comment_{comment.id}",
                'type': 'comment',
                'user': comment.user.username,
                'action': 'оставил комментарий',
                'target': 'к аниме',  # Можем улучшить если есть связь с аниме
                'time': time_str
            })
    except:
        # Если модель Comment не найдена, пропускаем
        pass
    
    # Получаем последние новости
    try:
        recent_news = News.objects.select_related('author').filter(
            created_at__gte=datetime.now() - timedelta(days=7)
        ).order_by('-created_at')[:3]
        
        for news in recent_news:
            time_diff = datetime.now() - news.created_at.replace(tzinfo=None)
            if time_diff.days > 0:
                time_str = f"{time_diff.days} дн. назад"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours} ч. назад"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                time_str = f"{minutes} мин. назад"
            else:
                time_str = "только что"
                
            recent_activities.append({
                'id': f"news_{news.id}",
                'type': 'news',
                'user': news.author.username,
                'action': 'опубликовал новость',
                'target': news.title[:30] + '...' if len(news.title) > 30 else news.title,
                'time': time_str
            })
    except:
        # Если модель News не найдена, пропускаем
        pass
    
    # Сортируем все активности по времени и берем последние 8
    # (сортировка по времени создания)
    all_activities = []
    
    # Добавляем пользователей с их временем регистрации
    for user in recent_users:
        all_activities.append({
            'time_obj': user.date_joined.replace(tzinfo=None),
            'data': {
                'id': f"user_{user.id}",
                'type': 'user_register',
                'user': user.username,
                'action': 'зарегистрировался',
                'time': ""  # Заполним после сортировки
            }
        })
    
    # Добавляем комментарии
    try:
        for comment in recent_comments:
            all_activities.append({
                'time_obj': comment.created_at.replace(tzinfo=None),
                'data': {
                    'id': f"comment_{comment.id}",
                    'type': 'comment',
                    'user': comment.user.username,
                    'action': 'оставил комментарий',
                    'target': 'к аниме',
                    'time': ""
                }
            })
    except:
        pass
    
    # Добавляем новости
    try:
        for news in recent_news:
            all_activities.append({
                'time_obj': news.created_at.replace(tzinfo=None),
                'data': {
                    'id': f"news_{news.id}",
                    'type': 'news',
                    'user': news.author.username,
                    'action': 'опубликовал новость',
                    'target': news.title[:30] + '...' if len(news.title) > 30 else news.title,
                    'time': ""
                }
            })
    except:
        pass
    
    # Сортируем по времени (новые сначала) и берем последние 8
    all_activities.sort(key=lambda x: x['time_obj'], reverse=True)
    all_activities = all_activities[:8]
    
    # Форматируем время для финального списка
    recent_activities = []
    for activity in all_activities:
        time_diff = datetime.now() - activity['time_obj']
        if time_diff.days > 0:
            time_str = f"{time_diff.days} дн. назад"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_str = f"{hours} ч. назад"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            time_str = f"{minutes} мин. назад"
        else:
            time_str = "только что"
        
        activity_data = activity['data']
        activity_data['time'] = time_str
        recent_activities.append(activity_data)
    
    return Response({
        'data': {
            'user_activity': user_activity,
            'content_views': content_views,
            'recent_activities': recent_activities
        }
    })
