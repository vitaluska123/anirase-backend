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
from core.utils.admin_logger import AdminLogger, AdminActionReverter

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
    sort_field = request.GET.get('sort_field', 'date_joined')
    sort_direction = request.GET.get('sort_direction', 'desc')
    
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
    
    # Сортировка
    allowed_sort_fields = ['username', 'email', 'date_joined', 'last_login', 'is_active', 'is_staff']
    if sort_field in allowed_sort_fields:
        if sort_direction == 'asc':
            order_field = sort_field
        else:
            order_field = f'-{sort_field}'
        
        # Обработка null значений для last_login
        if sort_field == 'last_login':
            if sort_direction == 'asc':
                users_query = users_query.order_by('last_login', 'date_joined')
            else:
                users_query = users_query.order_by('-last_login', '-date_joined')
        else:
            users_query = users_query.order_by(order_field)
    else:
        # По умолчанию сортируем по дате регистрации (новые сначала)
        users_query = users_query.order_by('-date_joined')
    
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
            'is_superuser': user.is_superuser,            'date_joined': user.date_joined.isoformat(),
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
    Получение полных аналитических данных для страницы Analytics
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)

    # Получаем параметр периода
    period = request.GET.get('period', '7d')
    
    # Определяем временные рамки
    now = timezone.now()
    if period == '24h':
        start_date = now - timedelta(hours=24)
        date_format = '%H:00'
        date_range = 24
        date_unit = 'hours'
    elif period == '7d':
        start_date = now - timedelta(days=7)
        date_format = '%d.%m'
        date_range = 7
        date_unit = 'days'
    elif period == '30d':
        start_date = now - timedelta(days=30)
        date_format = '%d.%m'
        date_range = 30
        date_unit = 'days'
    elif period == '90d':
        start_date = now - timedelta(days=90)
        date_format = '%d.%m'
        date_range = 90
        date_unit = 'days'
    else:
        start_date = now - timedelta(days=7)
        date_format = '%d.%m'
        date_range = 7
        date_unit = 'days'

    # === ОСНОВНЫЕ МЕТРИКИ ===
    
    # Всего пользователей
    total_users = User.objects.count()
    
    # Новые пользователи за период
    new_users = User.objects.filter(date_joined__gte=start_date).count()
    
    # Активные пользователи (те, кто комментировал или добавлял закладки за период)
    active_users = User.objects.filter(
        Q(comments__created_at__gte=start_date) |
        Q(bookmarks__created_at__gte=start_date) |
        Q(history__watched_at__gte=start_date)
    ).distinct().count()
    
    # Всего просмотров (история просмотров)
    total_views = History.objects.filter(watched_at__gte=start_date).count()
    
    # Всего комментариев за период
    total_comments = Comment.objects.filter(created_at__gte=start_date).count()
    
    # Комнаты за период
    active_rooms = Room.objects.filter(created_at__gte=start_date).count()
    total_rooms = Room.objects.count()

    # === ГРАФИКИ АКТИВНОСТИ ===
    
    # График активности пользователей
    user_activity_data = []
    
    if date_unit == 'hours':
        for i in range(date_range):
            hour_start = now - timedelta(hours=date_range-1-i)
            hour_end = hour_start + timedelta(hours=1)
            
            new_users_count = User.objects.filter(
                date_joined__gte=hour_start, 
                date_joined__lt=hour_end
            ).count()
            
            sessions_count = RoomSession.objects.filter(
                joined_at__gte=hour_start,
                joined_at__lt=hour_end
            ).count()
            
            user_activity_data.append({
                'name': hour_start.strftime(date_format),
                'users': new_users_count,
                'sessions': sessions_count
            })
    else:
        for i in range(date_range):
            day_start = (now - timedelta(days=date_range-1-i)).replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            new_users_count = User.objects.filter(
                date_joined__gte=day_start, 
                date_joined__lt=day_end
            ).count()
            
            sessions_count = RoomSession.objects.filter(
                joined_at__gte=day_start,
                joined_at__lt=day_end
            ).count()
            
            user_activity_data.append({
                'name': day_start.strftime(date_format),
                'users': new_users_count,
                'sessions': sessions_count
            })

    # === ТОП АНИМЕ (по просмотрам) ===
    
    # Получаем топ аниме по количеству просмотров
    top_anime_raw = History.objects.filter(watched_at__gte=start_date)\
        .values('anime_id')\
        .annotate(views=Count('id'))\
        .order_by('-views')[:10]
    
    top_anime_data = []
    for idx, anime in enumerate(top_anime_raw, 1):
        top_anime_data.append({
            'rank': idx,
            'title': f"Аниме {anime['anime_id'][:20]}",  # Ограничиваем длину
            'views': anime['views']
        })

    # === ТОП ПОЛЬЗОВАТЕЛИ (по активности) ===
    
    # Получаем топ пользователей по количеству активности
    top_users_raw = User.objects.filter(
        Q(comments__created_at__gte=start_date) |
        Q(history__watched_at__gte=start_date) |
        Q(hosted_rooms__created_at__gte=start_date)
    ).annotate(
        activity_count=Count('comments', filter=Q(comments__created_at__gte=start_date)) +
                      Count('history', filter=Q(history__watched_at__gte=start_date)) +
                      Count('hosted_rooms', filter=Q(hosted_rooms__created_at__gte=start_date))
    ).order_by('-activity_count')[:10]
    
    top_users_data = []
    for idx, user in enumerate(top_users_raw, 1):
        sessions_count = RoomSession.objects.filter(
            user=user, 
            joined_at__gte=start_date
        ).count()
        
        top_users_data.append({
            'rank': idx,
            'username': user.username,
            'sessions': sessions_count,
            'hours': round(sessions_count * 1.5, 1)  # Примерная оценка часов
        })

    # === СТАТИСТИКА КОНТЕНТА ===
    
    # Статистика по типам активности
    content_stats = []
    
    # Закладки по статусам
    bookmark_stats = Bookmark.objects.filter(created_at__gte=start_date)\
        .values('status')\
        .annotate(count=Count('id'))
    
    status_mapping = {
        'watching': 'Смотрю',
        'planned': 'Запланировано', 
        'completed': 'Просмотрено'
    }
    
    for stat in bookmark_stats:
        content_stats.append({
            'name': status_mapping.get(stat['status'], stat['status']),
            'value': stat['count'],
            'color': {
                'watching': '#10b981',
                'planned': '#f59e0b', 
                'completed': '#3b82f6'
            }.get(stat['status'], '#6b7280')
        })

    # === СТАТИСТИКА КОМНАТ ===
    
    # Статистика по комнатам
    room_stats = {
        'total_rooms': total_rooms,
        'active_rooms': active_rooms,
        'private_rooms': Room.objects.filter(is_private=True).count(),
        'public_rooms': Room.objects.filter(is_private=False).count(),
    }

    # === ТРЕНДЫ ===
    
    # Вычисляем тренды по сравнению с предыдущим периодом
    prev_period_start = start_date - (now - start_date)
    prev_period_end = start_date
    
    prev_users = User.objects.filter(
        date_joined__gte=prev_period_start,
        date_joined__lt=prev_period_end
    ).count()
    
    prev_views = History.objects.filter(
        watched_at__gte=prev_period_start,
        watched_at__lt=prev_period_end
    ).count()
    
    prev_comments = Comment.objects.filter(
        created_at__gte=prev_period_start,
        created_at__lt=prev_period_end
    ).count()

    # Вычисляем процентные изменения
    def calculate_trend(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)

    trends = {
        'users_trend': calculate_trend(new_users, prev_users),
        'views_trend': calculate_trend(total_views, prev_views),
        'comments_trend': calculate_trend(total_comments, prev_comments)
    }

    # Последняя активность (только 8 записей для превью)
    recent_activities = get_recent_activities(limit=8)
    
    return Response({
        'data': {
            # Основные метрики
            'total_users': total_users,
            'new_users': new_users,
            'active_users': active_users,
            'total_views': total_views,
            'total_comments': total_comments,
            'active_rooms': active_rooms,
            
            # Тренды
            'trends': trends,
            
            # Графики
            'user_activity': user_activity_data,
            'content_data': content_stats,
            
            # Топы
            'top_anime': top_anime_data,
            'top_users': top_users_data,
            
            # Статистика комнат
            'room_stats': room_stats,
            
            # Активность
            'recent_activities': recent_activities,
            
            # Метаданные
            'period': period,
            'period_start': start_date.isoformat(),
            'period_end': now.isoformat()
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
    Редактирование пользователя с логированием
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
    
    # Сохраняем старые данные для логирования
    old_data = {
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }
    
    # Получаем данные для обновления
    username = request.data.get('username')
    email = request.data.get('email')
    is_active = request.data.get('is_active')
    is_staff = request.data.get('is_staff')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    
    changes_made = False
    
    # Проверяем уникальность username и email (если они изменились)
    if username and username != user.username:
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Пользователь с таким именем уже существует'}, status=400)
        user.username = username
        changes_made = True
    
    if email and email != user.email:
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Пользователь с таким email уже существует'}, status=400)
        user.email = email
        changes_made = True
    
    # Обновляем имена
    if first_name != user.first_name:
        user.first_name = first_name
        changes_made = True
        
    if last_name != user.last_name:
        user.last_name = last_name
        changes_made = True
    
    # Обновляем статусы (только если пользователь не изменяет сам себя)
    if is_active is not None and user.id != request.user.id:
        if user.is_active != is_active:
            user.is_active = is_active
            changes_made = True
    
    if is_staff is not None and request.user.is_superuser and user.id != request.user.id:
        if user.is_staff != is_staff:
            user.is_staff = is_staff
            changes_made = True
    
    if changes_made:
        user.save()
        
        # Логируем изменения
        new_data = {
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        AdminLogger.log_user_action(
            admin_user=request.user,
            action_type='update',
            target_user=user,
            old_data=old_data,
            new_data=new_data,
            request=request
        )
    
    return Response({
        'message': 'Пользователь успешно обновлен',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'first_name': user.first_name,
            'last_name': user.last_name,
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
    Удаление пользователя с логированием
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
    
    # Сохраняем данные пользователя для логирования и возможного восстановления
    old_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None,
    }
    
    username = user.username
    
    # Логируем удаление ПЕРЕД фактическим удалением
    AdminLogger.log_user_action(
        admin_user=request.user,
        action_type='delete',
        target_user=user,
        old_data=old_data,
        new_data={},
        request=request
    )
    
    user.delete()
    
    return Response({
        'message': f'Пользователь {username} успешно удален'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dashboard_user_create(request):
    """
    Создание нового пользователя с логированием
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    # Получаем данные для создания
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    is_active = request.data.get('is_active', True)
    is_staff = request.data.get('is_staff', False)
    
    # Валидация обязательных полей
    if not username or not email or not password:
        return Response({'error': 'Имя пользователя, email и пароль обязательны'}, status=400)
    
    # Проверяем уникальность username и email
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Пользователь с таким именем уже существует'}, status=400)
    
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Пользователь с таким email уже существует'}, status=400)
    
    # Валидация пароля
    if len(password) < 6:
        return Response({'error': 'Пароль должен содержать минимум 6 символов'}, status=400)
    
    try:
        # Создаем пользователя
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_staff=is_staff if request.user.is_superuser else False  # Только суперпользователь может назначать staff
        )
        
        # Логируем создание пользователя
        new_data = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined.isoformat(),
        }
        
        AdminLogger.log_user_action(
            admin_user=request.user,
            action_type='create',
            target_user=user,
            old_data={},
            new_data=new_data,
            request=request
        )
        
        return Response({
            'message': 'Пользователь успешно создан',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': None
            }
        })
        
    except Exception as e:
        return Response({'error': f'Ошибка при создании пользователя: {str(e)}'}, status=500)

# === УПРАВЛЕНИЕ КОММЕНТАРИЯМИ ===

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_comments(request):
    """
    Получение списка комментариев для управления
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    search = request.GET.get('search', '')
    anime_id = request.GET.get('anime_id', '')
    sort_field = request.GET.get('sort_field', 'created_at')
    sort_direction = request.GET.get('sort_direction', 'desc')
    
    try:
        comments_query = Comment.objects.select_related('user').all()
        
        # Поиск
        if search:
            comments_query = comments_query.filter(
                Q(text__icontains=search) | 
                Q(user__username__icontains=search) |
                Q(anime_id__icontains=search)
            )
        
        # Фильтр по аниме
        if anime_id:
            comments_query = comments_query.filter(anime_id=anime_id)
        
        # Сортировка
        allowed_sort_fields = ['created_at', 'updated_at', 'user__username', 'anime_id']
        if sort_field in allowed_sort_fields:
            if sort_direction == 'asc':
                order_field = sort_field
            else:
                order_field = f'-{sort_field}'
            comments_query = comments_query.order_by(order_field)
        else:
            comments_query = comments_query.order_by('-created_at')
        
        total = comments_query.count()
        comments = comments_query[(page-1)*limit:page*limit]
        
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'text': comment.text,
                'anime_id': comment.anime_id,
                'user': comment.user.username,
                'user_id': comment.user.id,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat(),
                'parent_id': comment.parent.id if comment.parent else None,
                'replies_count': comment.replies.count() if hasattr(comment, 'replies') else 0,
                'likes_count': comment.likes_count
            })
        
        return Response({
            'data': comments_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        return Response({'error': f'Ошибка при получении комментариев: {str(e)}'}, status=500)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def dashboard_comment_delete(request, comment_id):
    """
    Удаление комментария с логированием
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        comment = Comment.objects.get(id=comment_id)
        
        # Сохраняем данные для логирования (очищаем от проблемных символов)
        old_data = {
            'id': comment.id,
            'user_id': comment.user.id if comment.user else None,
            'user_username': comment.user.username if comment.user else 'Неизвестный',
            'anime_id': comment.anime_id,
            'text': comment.text.encode('ascii', 'ignore').decode('ascii') if comment.text else '',
            'created_at': comment.created_at.isoformat() if comment.created_at else '',
            'parent_id': comment.parent.id if comment.parent else None,
            'likes_count': getattr(comment, 'likes_count', 0)
        }
        
        # Безопасно получаем текст для сообщения
        comment_text = comment.text[:50] + '...' if comment.text and len(comment.text) > 50 else (comment.text or 'Без текста')
        safe_comment_text = comment_text.encode('ascii', 'ignore').decode('ascii')
        
        # Логируем удаление
        AdminLogger.log_comment_action(
            admin_user=request.user,
            action_type='delete',
            comment_obj=comment,
            old_data=old_data,
            new_data={},
            request=request
        )
        
        comment.delete()
        
        return Response({
            'message': f'Комментарий "{safe_comment_text}" успешно удален'
        })
        
    except Comment.DoesNotExist:
        return Response({'error': 'Комментарий не найден'}, status=404)
    except Exception as e:
        return Response({'error': f'Ошибка при удалении комментария: {str(e)}'}, status=500)

# === УПРАВЛЕНИЕ НОВОСТЯМИ ===

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_news(request):
    """
    Получение списка новостей для управления
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    search = request.GET.get('search', '')
    published = request.GET.get('published', '')
    sort_field = request.GET.get('sort_field', 'created_at')
    sort_direction = request.GET.get('sort_direction', 'desc')
    
    try:
        news_query = News.objects.all()
        
        # Поиск
        if search:
            news_query = news_query.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search) |
                Q(excerpt__icontains=search)
            )
        
        # Фильтр по статусу публикации
        if published == 'true':
            news_query = news_query.filter(is_published=True)
        elif published == 'false':
            news_query = news_query.filter(is_published=False)
        
        # Сортировка
        allowed_sort_fields = ['created_at', 'updated_at', 'title', 'is_published']
        if sort_field in allowed_sort_fields:
            if sort_direction == 'asc':
                order_field = sort_field
            else:
                order_field = f'-{sort_field}'
            news_query = news_query.order_by(order_field)
        else:
            news_query = news_query.order_by('-created_at')
        
        total = news_query.count()
        news = news_query[(page-1)*limit:page*limit]
        
        news_data = []
        for item in news:
            news_data.append({
                'id': item.id,
                'title': item.title,
                'excerpt': item.excerpt or (item.content[:200] + '...' if len(item.content) > 200 else item.content),
                'is_published': item.is_published,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
                'banner': item.banner.url if item.banner else None,
                'tags_count': item.tags.count()
            })
        
        return Response({
            'data': news_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        return Response({'error': f'Ошибка при получении новостей: {str(e)}'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_news_detail(request, news_id):
    """
    Получение полной информации о конкретной новости для редактирования
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        news = News.objects.get(id=news_id)
        
        return Response({
            'data': {
                'id': news.id,
                'title': news.title,
                'content': news.content,
                'excerpt': news.excerpt,
                'is_published': news.is_published,
                'created_at': news.created_at.isoformat(),
                'updated_at': news.updated_at.isoformat(),
                'banner': news.banner.url if news.banner else None,
                'tags': [tag.name for tag in news.tags.all()]
            }
        })
        
    except News.DoesNotExist:
        return Response({'error': 'Новость не найдена'}, status=404)
    except Exception as e:
        return Response({'error': f'Ошибка при получении новости: {str(e)}'}, status=500)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def dashboard_news_toggle_published(request, news_id):
    """
    Переключение статуса публикации новости с логированием
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        news = News.objects.get(id=news_id)
        
        # Сохраняем старые данные
        old_data = {
            'is_published': news.is_published
        }
        
        news.is_published = not news.is_published
        news.save()
        
        # Новые данные
        new_data = {
            'is_published': news.is_published
        }
        
        # Логируем изменение статуса
        AdminLogger.log_news_action(
            admin_user=request.user,
            action_type='status_change',
            news_obj=news,
            old_data=old_data,
            new_data=new_data,
            request=request
        )
        
        return Response({
            'message': f'Новость "{news.title}" {"опубликована" if news.is_published else "снята с публикации"}',
            'is_published': news.is_published
        })
        
    except News.DoesNotExist:
        return Response({'error': 'Новость не найдена'}, status=404)
    except Exception as e:
        return Response({'error': f'Ошибка при изменении статуса новости: {str(e)}'}, status=500)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def dashboard_news_delete(request, news_id):
    """
    Удаление новости с логированием
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        news = News.objects.get(id=news_id)
        
        # Сохраняем данные для логирования
        old_data = {
            'id': news.id,
            'title': news.title,
            'content': news.content[:100] + '...' if len(news.content) > 100 else news.content,
            'excerpt': news.excerpt,
            'is_published': news.is_published,
            'created_at': news.created_at.isoformat(),
            'updated_at': news.updated_at.isoformat(),
            'tags': [tag.name for tag in news.tags.all()]
        }
        
        news_title = news.title
        
        # Логируем удаление
        AdminLogger.log_news_action(
            admin_user=request.user,
            action_type='delete',
            news_obj=news,
            old_data=old_data,
            new_data={},
            request=request
        )
        
        news.delete()
        
        return Response({
            'message': f'Новость "{news_title}" успешно удалена'
        })
        
    except News.DoesNotExist:
        return Response({'error': 'Новость не найдена'}, status=404)
    except Exception as e:
        return Response({'error': f'Ошибка при удалении новости: {str(e)}'}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dashboard_news_create(request):
    """
    Создание новой новости с логированием
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    # Получаем данные для создания
    title = request.data.get('title')
    content = request.data.get('content')
    excerpt = request.data.get('excerpt', '')
    is_published = request.data.get('is_published', False)
    tags = request.data.get('tags', [])
    
    # Валидация обязательных полей
    if not title or not content:
        return Response({'error': 'Заголовок и содержимое обязательны'}, status=400)
    
    try:
        # Создаем новость
        news = News.objects.create(
            title=title,
            content=content,
            excerpt=excerpt,
            is_published=is_published
        )
        
        # Добавляем теги
        if tags:
            # Создаем теги, если они не существуют
            tag_objects = []
            for tag_name in tags:
                tag, created = Tag.objects.get_or_create(name=tag_name.strip())
                tag_objects.append(tag)
            news.tags.set(tag_objects)
        
        # Логируем создание новости
        new_data = {
            'id': news.id,
            'title': news.title,
            'content': news.content[:100] + '...' if len(news.content) > 100 else news.content,
            'excerpt': news.excerpt,
            'is_published': news.is_published,
            'created_at': news.created_at.isoformat(),
            'tags': [tag.name for tag in news.tags.all()]
        }
        
        AdminLogger.log_news_action(
            admin_user=request.user,
            action_type='create',
            news_obj=news,
            old_data={},
            new_data=new_data,
            request=request
        )
        
        return Response({
            'message': 'Новость успешно создана',
            'news': {
                'id': news.id,
                'title': news.title,
                'content': news.content,
                'excerpt': news.excerpt,
                'is_published': news.is_published,
                'created_at': news.created_at.isoformat(),
                'updated_at': news.updated_at.isoformat(),
                'tags': [tag.name for tag in news.tags.all()]
            }
        })
        
    except Exception as e:
        return Response({'error': f'Ошибка при создании новости: {str(e)}'}, status=500)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def dashboard_news_edit(request, news_id):
    """
    Редактирование новости с логированием
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        news = News.objects.get(id=news_id)
    except News.DoesNotExist:
        return Response({'error': 'Новость не найдена'}, status=404)
    
    # Сохраняем старые данные для логирования
    old_data = {
        'id': news.id,
        'title': news.title,
        'content': news.content[:100] + '...' if len(news.content) > 100 else news.content,
        'excerpt': news.excerpt,
        'is_published': news.is_published,
        'updated_at': news.updated_at.isoformat(),
        'tags': [tag.name for tag in news.tags.all()]
    }
    
    # Получаем данные для обновления
    title = request.data.get('title')
    content = request.data.get('content')
    excerpt = request.data.get('excerpt')
    is_published = request.data.get('is_published')
    tags = request.data.get('tags')
    
    # Валидация обязательных полей
    if title is not None and not title.strip():
        return Response({'error': 'Заголовок не может быть пустым'}, status=400)
    if content is not None and not content.strip():
        return Response({'error': 'Содержимое не может быть пустым'}, status=400)
    
    try:
        changes_made = False
        
        # Обновляем поля
        if title is not None and title != news.title:
            news.title = title
            changes_made = True
        if content is not None and content != news.content:
            news.content = content
            changes_made = True
        if excerpt is not None and excerpt != news.excerpt:
            news.excerpt = excerpt
            changes_made = True
        if is_published is not None and is_published != news.is_published:
            news.is_published = is_published
            changes_made = True
            
        if changes_made:
            news.save()
        
        # Обновляем теги
        if tags is not None:
            old_tags = set(tag.name for tag in news.tags.all())
            new_tags = set(tag.strip() for tag in tags if tag.strip())
            
            if old_tags != new_tags:
                tag_objects = []
                for tag_name in new_tags:
                    tag, created = Tag.objects.get_or_create(name=tag_name)
                    tag_objects.append(tag)
                news.tags.set(tag_objects)
                changes_made = True
        
        if changes_made:
            # Логируем изменения
            new_data = {
                'id': news.id,
                'title': news.title,
                'content': news.content[:100] + '...' if len(news.content) > 100 else news.content,
                'excerpt': news.excerpt,
                'is_published': news.is_published,
                'updated_at': news.updated_at.isoformat(),
                'tags': [tag.name for tag in news.tags.all()]
            }
            
            AdminLogger.log_news_action(
                admin_user=request.user,
                action_type='update',
                news_obj=news,
                old_data=old_data,
                new_data=new_data,
                request=request
            )
        
        return Response({
            'message': 'Новость успешно обновлена',
            'news': {
                'id': news.id,
                'title': news.title,
                'content': news.content,
                'excerpt': news.excerpt,
                'is_published': news.is_published,
                'created_at': news.created_at.isoformat(),
                'updated_at': news.updated_at.isoformat(),
                'tags': [tag.name for tag in news.tags.all()]
            }
        })
        
    except Exception as e:
        return Response({'error': f'Ошибка при обновлении новости: {str(e)}'}, status=500)

# === УПРАВЛЕНИЕ КОМНАТАМИ ===

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_rooms(request):
    """
    Получение списка комнат для dashboard
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        search = request.GET.get('search', '')
        is_private = request.GET.get('is_private')
        sort_field = request.GET.get('sort_field', 'created_at')
        sort_direction = request.GET.get('sort_direction', 'desc')
        
        rooms_query = Room.objects.select_related('host').prefetch_related('sessions')
        
        # Поиск по ID комнаты, ID аниме или хосту
        if search:
            rooms_query = rooms_query.filter(
                Q(room_id__icontains=search) | 
                Q(anime_id__icontains=search) |
                Q(host__username__icontains=search)
            )
        
        # Фильтр по приватности
        if is_private is not None:
            if is_private.lower() == 'true':
                rooms_query = rooms_query.filter(is_private=True)
            elif is_private.lower() == 'false':
                rooms_query = rooms_query.filter(is_private=False)
        
        # Сортировка
        allowed_sort_fields = ['created_at', 'room_id', 'anime_id', 'is_private']
        if sort_field in allowed_sort_fields:
            if sort_direction == 'asc':
                order_field = sort_field
            else:
                order_field = f'-{sort_field}'
            rooms_query = rooms_query.order_by(order_field)
        else:
            rooms_query = rooms_query.order_by('-created_at')
        
        total = rooms_query.count()
        rooms = rooms_query[(page-1)*limit:page*limit]
        
        rooms_data = []
        for room in rooms:
            active_sessions = room.sessions.count()
            rooms_data.append({
                'id': room.id,
                'room_id': room.room_id,
                'anime_id': room.anime_id,
                'host': room.host.username if room.host else None,
                'host_id': room.host.id if room.host else None,
                'is_private': room.is_private,
                'allow_control': room.allow_control,
                'active_sessions': active_sessions,
                'created_at': room.created_at.isoformat()
            })
        
        return Response({
            'data': rooms_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        return Response({'error': f'Ошибка при получении комнат: {str(e)}'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_rooms_stats(request):
    """
    Получение статистики комнат для dashboard
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Общая статистика
        total_rooms = Room.objects.count()
        active_rooms = Room.objects.filter(sessions__isnull=False).distinct().count()
        private_rooms = Room.objects.filter(is_private=True).count()
        public_rooms = Room.objects.filter(is_private=False).count()
        
        # Статистика сессий
        total_sessions = RoomSession.objects.count()
        
        # Топ аниме по комнатам
        from django.db.models import Count
        top_anime = Room.objects.values('anime_id').annotate(
            room_count=Count('id')
        ).order_by('-room_count')[:10]
        
        # Комнаты за последние 7 дней
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_rooms = Room.objects.filter(created_at__gte=seven_days_ago).count()
        
        return Response({
            'data': {
                'total_rooms': total_rooms,
                'active_rooms': active_rooms,
                'private_rooms': private_rooms,
                'public_rooms': public_rooms,
                'total_sessions': total_sessions,
                'recent_rooms': recent_rooms,
                'top_anime': list(top_anime)
            }
        })
        
    except Exception as e:
        return Response({'error': f'Ошибка при получении статистики комнат: {str(e)}'}, status=500)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def dashboard_room_delete(request, room_id):
    """
    Удаление комнаты
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    try:
        room = Room.objects.get(room_id=room_id)
        room_name = room.room_id
        room.delete()
        
        return Response({
            'message': f'Комната {room_name} успешно удалена'
        })
        
    except Room.DoesNotExist:
        return Response({'error': 'Комната не найдена'}, status=404)
    except Exception as e:
        return Response({'error': f'Ошибка при удалении комнаты: {str(e)}'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_room_sessions(request, room_id):
    """
    Получение сессий конкретной комнаты
    """
    is_allowed, error = check_staff_permission(request.user)
    if not is_allowed:
        return Response(error, status=status.HTTP_403_FORBIDDEN)
    try:
        room = Room.objects.get(room_id=room_id)
        sessions = RoomSession.objects.filter(room=room).select_related('user')
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'user': session.user.username if session.user else 'Anonymous',
                'user_id': session.user.id if session.user else None,
                'session_key': session.session_key,
                'joined_at': session.joined_at.isoformat()
            })
        
        return Response({
            'data': {
                'room': {
                    'id': room.id,
                    'room_id': room.room_id,
                    'anime_id': room.anime_id,
                    'host': room.host.username if room.host else None,
                    'is_private': room.is_private,
                    'allow_control': room.allow_control
                },
                'sessions': sessions_data
            }
        })
        
    except Room.DoesNotExist:
        return Response({'error': 'Комната не найдена'}, status=404)
    except Exception as e:
        return Response({'error': f'Ошибка при получении сессий: {str(e)}'}, status=500)

# === ЛОГИ ДЕЙСТВИЙ АДМИНИСТРАТОРОВ ===

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_admin_logs(request):
    """
    Получение логов действий администраторов (только для суперпользователей)
    """
    # Проверяем, что пользователь - суперпользователь
    if not request.user.is_superuser:
        return Response({
            'error': 'Access denied', 
            'message': 'Доступ к логам администраторов разрешен только для суперпользователей'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Параметры пагинации и фильтрации
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 50)), 100)  # Максимум 100 записей
    admin_user = request.GET.get('admin_user')
    action_type = request.GET.get('action_type')
    entity_type = request.GET.get('entity_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Базовый запрос
    queryset = AdminActionLog.objects.select_related('admin_user', 'reverted_by').all()
    
    # Применяем фильтры
    if admin_user:
        queryset = queryset.filter(admin_user__username__icontains=admin_user)
    
    if action_type:
        queryset = queryset.filter(action_type=action_type)
    
    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)
    
    if date_from:
        try:
            date_from_parsed = timezone.datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            queryset = queryset.filter(created_at__gte=date_from_parsed)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_parsed = timezone.datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            queryset = queryset.filter(created_at__lte=date_to_parsed)
        except ValueError:
            pass
    
    # Подсчет общего количества
    total_count = queryset.count()
    
    # Пагинация
    offset = (page - 1) * limit
    logs = queryset[offset:offset + limit]
    
    # Формируем данные для ответа
    logs_data = []
    for log in logs:
        logs_data.append({
            'id': log.id,
            'admin_user': {
                'id': log.admin_user.id,
                'username': log.admin_user.username,
                'email': log.admin_user.email
            },
            'action_type': log.action_type,
            'action_type_display': log.get_action_type_display(),
            'entity_type': log.entity_type,
            'entity_type_display': log.get_entity_type_display(),
            'entity_id': log.entity_id,
            'entity_name': log.entity_name,
            'description': log.description,
            'ip_address': log.ip_address,
            'is_reverted': log.is_reverted,
            'can_be_reverted': log.can_be_reverted(),
            'revert_description': log.get_revert_description(),
            'reverted_at': log.reverted_at.isoformat() if log.reverted_at else None,
            'reverted_by': {
                'id': log.reverted_by.id,
                'username': log.reverted_by.username
            } if log.reverted_by else None,
            'revert_reason': log.revert_reason,
            'created_at': log.created_at.isoformat(),
            'old_data': log.old_data,
            'new_data': log.new_data
        })
    
    # Статистика для фильтров
    action_types = AdminActionLog.objects.values_list('action_type', flat=True).distinct()
    entity_types = AdminActionLog.objects.values_list('entity_type', flat=True).distinct()
    
    return Response({
        'data': {
            'logs': logs_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            },
            'filters': {
                'action_types': list(action_types),
                'entity_types': list(entity_types)
            }
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dashboard_admin_log_revert(request, log_id):
    """
    Откат действия администратора (только для суперпользователей)
    """
    # Проверяем, что пользователь - суперпользователь
    if not request.user.is_superuser:
        return Response({
            'error': 'Access denied', 
            'message': 'Доступ к откату действий администраторов разрешен только для суперпользователей'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        log = AdminActionLog.objects.get(id=log_id)
    except AdminActionLog.DoesNotExist:
        return Response({'error': 'Лог действия не найден'}, status=404)
    
    if not log.can_be_reverted():
        return Response({'error': 'Это действие нельзя откатить'}, status=400)
    
    if log.is_reverted:
        return Response({'error': 'Это действие уже было откачено'}, status=400)
    
    # Получаем причину отката
    reason = request.data.get('reason', '')
    if not reason:
        return Response({'error': 'Укажите причину отката'}, status=400)
    
    # Выполняем откат
    success = AdminActionReverter.revert_action(log, request.user, reason)
    
    if success:
        # Логируем сам факт отката
        AdminLogger.log_action(
            admin_user=request.user,
            action_type='system_action',
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            entity_name=f"Откат действия: {log.entity_name}",
            old_data={'reverted_log_id': log.id},
            new_data={'revert_reason': reason},
            description=f"Откат действия {log.get_action_type_display()} для {log.entity_name}",
            request=request
        )
        
        return Response({
            'message': 'Действие успешно откачено',
            'reverted_at': log.reverted_at.isoformat() if log.reverted_at else None
        })
    else:
        return Response({'error': 'Не удалось откатить действие'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_admin_logs_stats(request):
    """
    Статистика по логам действий администраторов (только для суперпользователей)
    """
    # Проверяем, что пользователь - суперпользователь
    if not request.user.is_superuser:
        return Response({
            'error': 'Access denied', 
            'message': 'Доступ к логам администраторов разрешен только для суперпользователей'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Период для статистики
    period = request.GET.get('period', '7d')
    now = timezone.now()
    
    if period == '24h':
        start_date = now - timedelta(hours=24)
    elif period == '7d':
        start_date = now - timedelta(days=7)
    elif period == '30d':
        start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(days=7)
    
    # Общая статистика
    total_actions = AdminActionLog.objects.filter(created_at__gte=start_date).count()
    reverted_actions = AdminActionLog.objects.filter(
        created_at__gte=start_date,
        is_reverted=True
    ).count()
    
    # Статистика по типам действий
    actions_by_type = AdminActionLog.objects.filter(created_at__gte=start_date)\
        .values('action_type')\
        .annotate(count=Count('id'))\
        .order_by('-count')
      # Статистика по администраторам
    actions_by_admin = AdminActionLog.objects.filter(created_at__gte=start_date)\
        .values('admin_user__username')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:10]
    
    # Количество уникальных активных администраторов
    active_admins_count = AdminActionLog.objects.filter(created_at__gte=start_date)\
        .values('admin_user')\
        .distinct()\
        .count()
    
    # Статистика по типам сущностей
    actions_by_entity = AdminActionLog.objects.filter(created_at__gte=start_date)\
        .values('entity_type')\
        .annotate(count=Count('id'))\
        .order_by('-count')
    
    return Response({
        'data': {
            'period': period,
            'total_actions': total_actions,
            'reverted_actions': reverted_actions,
            'revert_rate': round((reverted_actions / total_actions * 100) if total_actions > 0 else 0, 1),
            'active_admins_count': active_admins_count,
            'actions_by_type': list(actions_by_type),
            'actions_by_admin': list(actions_by_admin),
            'actions_by_entity': list(actions_by_entity)
        }
    })
