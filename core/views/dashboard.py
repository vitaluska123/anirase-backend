# dashboard/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.utils import timezone
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

def format_time_ago(target_time):
    """
    Форматирует время в понятный формат "X минут назад"
    """
    if target_time.tzinfo is not None:
        now = timezone.now()
        time_diff = now - target_time
    else:
        now = datetime.now()
        time_diff = now - target_time
    
    total_seconds = int(time_diff.total_seconds())
    
    if total_seconds < 60:
        return "только что"
    elif total_seconds < 3600:  # меньше часа
        minutes = total_seconds // 60
        return f"{minutes} мин. назад"
    elif total_seconds < 86400:  # меньше дня
        hours = total_seconds // 3600
        return f"{hours} ч. назад"
    elif total_seconds < 2592000:  # меньше месяца (30 дней)
        days = total_seconds // 86400
        return f"{days} дн. назад"
    else:  # больше месяца
        months = total_seconds // 2592000
        return f"{months} мес. назад"

def get_recent_activities(limit=8):
    """
    Получает последнюю активность пользователей
    """
    all_activities = []
    
    # Получаем последних зарегистрированных пользователей
    recent_users = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=30)
    ).order_by('-date_joined')[:50]
    
    for user in recent_users:
        all_activities.append({
            'time_obj': user.date_joined,
            'data': {
                'id': f"user_{user.id}",
                'type': 'user_register',
                'user': user.username,
                'action': 'зарегистрировался',
                'time': ""  # Заполним после сортировки
            }
        })
    
    # Получаем последние комментарии
    try:
        recent_comments = Comment.objects.select_related('user').filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('-created_at')[:50]
        
        for comment in recent_comments:
            all_activities.append({
                'time_obj': comment.created_at,
                'data': {
                    'id': f"comment_{comment.id}",
                    'type': 'comment',
                    'user': comment.user.username,
                    'action': 'оставил комментарий',
                    'target': 'к аниме',  # Можем улучшить если есть связь с аниме
                    'time': ""
                }
            })
    except:
        # Если модель Comment не найдена, пропускаем
        pass
    
    # Получаем последние новости
    try:
        recent_news = News.objects.select_related('author').filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('-created_at')[:50]
        
        for news in recent_news:
            all_activities.append({
                'time_obj': news.created_at,
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
        # Если модель News не найдена, пропускаем
        pass    # Сортируем по времени (новые сначала) и берем нужное количество
    all_activities.sort(key=lambda x: x['time_obj'], reverse=True)
    all_activities = all_activities[:limit]
    
    # Возвращаем время как timestamp для обработки на клиенте
    recent_activities = []
    for activity in all_activities:
        activity_data = activity['data']
        # Конвертируем время в timestamp (миллисекунды)
        time_obj = activity['time_obj']
        
        # Делаем время timezone-aware если оно naive
        if timezone.is_naive(time_obj):
            time_obj = timezone.make_aware(time_obj)
        
        activity_data['timestamp'] = int(time_obj.timestamp() * 1000)
        
        # Убираем старое поле time, заменяем на timestamp
        if 'time' in activity_data:
            del activity_data['time']
            
        recent_activities.append(activity_data)
    
    return recent_activities

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
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_users_month = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    
    # Активные пользователи (заходили за последние 7 дней)
    week_ago = timezone.now() - timedelta(days=7)
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
    is_active = request.GET.get('is_active')
    is_staff = request.GET.get('is_staff')
    
    users_query = User.objects.all()
    
    if search:
        users_query = users_query.filter(
            Q(username__icontains=search) | 
            Q(email__icontains=search)
        )
    
    # Фильтр по статусу активности
    if is_active is not None:
        if is_active.lower() == 'true':
            users_query = users_query.filter(is_active=True)
        elif is_active.lower() == 'false':
            users_query = users_query.filter(is_active=False)
    
    # Фильтр по роли (staff)
    if is_staff is not None:
        if is_staff.lower() == 'true':
            users_query = users_query.filter(is_staff=True)
        elif is_staff.lower() == 'false':
            users_query = users_query.filter(is_staff=False)
    total = users_query.count()
    users = users_query.order_by('-date_joined')[(page-1)*limit:page*limit]
    
    users_data = []
    for user in users:        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
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
        published_news = News.objects.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()
    except:
        news_count = 0
        published_news = 0
    
    # Статистика комментариев
    try:
        comments_count = Comment.objects.count()
        recent_comments = Comment.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
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
        date = timezone.now() - timedelta(days=29-i)
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
    
    # Последняя активность (только 8 записей для превью)
    recent_activities = get_recent_activities(limit=8)
    
    return Response({
        'data': {
            'user_activity': user_activity,
            'content_views': content_views,
            'recent_activities': recent_activities
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_activity_full(request):
    """
    Получение полной активности для модального окна (до 200 записей)
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    # Получаем параметры запроса
    limit = int(request.GET.get('limit', 200))  # По умолчанию 200
    activity_type = request.GET.get('type', 'all')  # Фильтр по типу
    
    # Ограничиваем максимальное количество записей
    if limit > 500:
        limit = 500
    
    # Получаем активность
    all_activities = get_recent_activities(limit=limit)
    
    # Фильтруем по типу если указан
    if activity_type != 'all':
        all_activities = [
            activity for activity in all_activities 
            if activity['type'] == activity_type
        ]
      # Группируем по типам для статистики
    type_counts = {}
    for activity in all_activities:
        activity_type = activity['type']
        type_counts[activity_type] = type_counts.get(activity_type, 0) + 1
    
    return Response({
        'data': {
            'recent_activities': all_activities,
            'total_count': len(all_activities),
            'type_counts': type_counts,
            'available_types': list(type_counts.keys())
        }
    })

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def dashboard_user_edit(request, user_id):
    """
    Редактирование пользователя
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=404)
    
    # Проверяем, что нельзя редактировать суперпользователя, если сам не суперпользователь
    if user.is_superuser and not request.user.is_superuser:
        return Response({'error': 'Недостаточно прав для редактирования этого пользователя'}, status=403)
    
    # Получаем данные для обновления
    username = request.data.get('username')
    email = request.data.get('email')
    is_active = request.data.get('is_active')
    is_staff = request.data.get('is_staff')
    
    # Проверяем уникальность username и email (если они изменились)
    if username and username != user.username:
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Пользователь с таким именем уже существует'}, status=400)
        user.username = username
    
    if email and email != user.email:
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Пользователь с таким email уже существует'}, status=400)
        user.email = email
    
    # Обновляем статусы (только если пользователь не изменяет сам себя)
    if is_active is not None and user.id != request.user.id:
        user.is_active = is_active
    
    if is_staff is not None and request.user.is_superuser and user.id != request.user.id:
        user.is_staff = is_staff
    
    user.save()
    
    return Response({
        'message': 'Пользователь успешно обновлен',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
    })

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def dashboard_user_toggle_active(request, user_id):
    """
    Блокировка/разблокировка пользователя
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=404)
    
    # Проверяем, что нельзя блокировать суперпользователя или самого себя
    if user.is_superuser:
        return Response({'error': 'Нельзя блокировать суперпользователя'}, status=403)
    
    if user.id == request.user.id:
        return Response({'error': 'Нельзя блокировать самого себя'}, status=403)
    
    # Переключаем статус активности
    user.is_active = not user.is_active
    user.save()
    
    action = 'разблокирован' if user.is_active else 'заблокирован'
    
    return Response({
        'message': f'Пользователь {action}',
        'is_active': user.is_active
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def dashboard_user_delete(request, user_id):
    """
    Удаление пользователя
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=404)
    
    # Проверяем, что нельзя удалить суперпользователя или самого себя
    if user.is_superuser:
        return Response({'error': 'Нельзя удалить суперпользователя'}, status=403)
    
    if user.id == request.user.id:
        return Response({'error': 'Нельзя удалить самого себя'}, status=403)
    
    username = user.username
    user.delete()
    
    return Response({
        'message': f'Пользователь {username} успешно удален'
    })
