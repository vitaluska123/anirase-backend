from django.contrib.auth.models import User
from django.utils import timezone
from core.models import AdminActionLog, AdminActionRevert
import json
from typing import Dict, Any, Optional

class AdminLogger:
    """Утилита для логирования действий администраторов"""
    
    @staticmethod
    def get_client_ip(request):
        """Получает IP адрес клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def sanitize_data(data):
        """Очищает данные от проблемных Unicode символов"""
        if data is None:
            return data
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                sanitized[key] = AdminLogger.sanitize_data(value)
            return sanitized
        elif isinstance(data, list):
            return [AdminLogger.sanitize_data(item) for item in data]
        elif isinstance(data, str):
            # Заменяем проблемные Unicode символы на их ASCII эквиваленты
            try:
                # Пытаемся закодировать и декодировать строку
                return data.encode('ascii', 'ignore').decode('ascii')
            except:
                # Если не удается, возвращаем очищенную версию
                return ''.join(char if ord(char) < 128 else '?' for char in data)
        else:
            return data

    @staticmethod
    def log_action(
        admin_user: User,
        action_type: str,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        old_data: Dict[str, Any] = None,
        new_data: Dict[str, Any] = None,        description: str = "",
        request=None
    ) -> AdminActionLog:
        """
        Логирует действие администратора
        
        Args:
            admin_user: Пользователь-администратор
            action_type: Тип действия (create, update, delete, etc.)
            entity_type: Тип сущности (user, news, comment, etc.)
            entity_id: ID сущности
            entity_name: Название/описание сущности
            old_data: Данные до изменения
            new_data: Данные после изменения
            description: Описание действия
            request: HTTP запрос для получения IP и User-Agent
        """
        
        # Подготавливаем данные
        old_data = old_data or {}
        new_data = new_data or {}
        
        # Очищаем данные от проблемных Unicode символов
        old_data = AdminLogger.sanitize_data(old_data)
        new_data = AdminLogger.sanitize_data(new_data)
        
        # Убираем чувствительные данные из логов
        sensitive_fields = ['password', 'token', 'secret', 'key']
        for data_dict in [old_data, new_data]:
            for field in sensitive_fields:
                if field in data_dict:
                    data_dict[field] = '[СКРЫТО]'
        
        # Получаем метаданные запроса
        ip_address = None
        user_agent = ""
        if request:
            ip_address = AdminLogger.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Ограничиваем длину
        
        # Создаем лог
        log_entry = AdminActionLog.objects.create(
            admin_user=admin_user,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            entity_name=entity_name[:500],  # Ограничиваем длину
            old_data=old_data,
            new_data=new_data,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return log_entry

    @staticmethod
    def log_user_action(admin_user: User, action_type: str, target_user: User, old_data: Dict = None, new_data: Dict = None, request=None):
        """Логирует действие с пользователем"""
        return AdminLogger.log_action(
            admin_user=admin_user,
            action_type=action_type,
            entity_type='user',
            entity_id=target_user.id,
            entity_name=f"{target_user.username} ({target_user.email})",
            old_data=old_data,
            new_data=new_data,
            description=f"Действие с пользователем {target_user.username}",
            request=request
        )

    @staticmethod
    def log_news_action(admin_user: User, action_type: str, news_obj, old_data: Dict = None, new_data: Dict = None, request=None):
        """Логирует действие с новостью"""
        return AdminLogger.log_action(
            admin_user=admin_user,
            action_type=action_type,
            entity_type='news',
            entity_id=news_obj.id,
            entity_name=news_obj.title,            old_data=old_data,
            new_data=new_data,
            description=f"Действие с новостью '{news_obj.title}'",
            request=request
        )

    @staticmethod
    def log_comment_action(admin_user: User, action_type: str, comment_obj, old_data: Dict = None, new_data: Dict = None, request=None):
        """Логирует действие с комментарием"""
        try:
            # Безопасно получаем имя пользователя
            username = getattr(comment_obj.user, 'username', 'Неизвестный пользователь') if hasattr(comment_obj, 'user') and comment_obj.user else 'Неизвестный пользователь'
            
            # Безопасно получаем текст комментария
            comment_text = getattr(comment_obj, 'text', '') if hasattr(comment_obj, 'text') else ''
            # Ограничиваем длину и очищаем от проблемных символов
            safe_text = comment_text[:50] if comment_text else 'Без текста'
            
            return AdminLogger.log_action(
                admin_user=admin_user,
                action_type=action_type,
                entity_type='comment',
                entity_id=comment_obj.id,
                entity_name=f"Комментарий от {username}: {safe_text}...",
                old_data=old_data,
                new_data=new_data,
                description=f"Действие с комментарием от {username}",
                request=request
            )
        except Exception as e:
            # В случае ошибки, создаем упрощенный лог
            return AdminLogger.log_action(
                admin_user=admin_user,
                action_type=action_type,
                entity_type='comment',
                entity_id=getattr(comment_obj, 'id', 'unknown'),
                entity_name=f"Комментарий #{getattr(comment_obj, 'id', 'unknown')}",
                old_data=old_data,
                new_data=new_data,
                description=f"Действие с комментарием (ошибка получения деталей: {str(e)})",
                request=request
            )

    @staticmethod
    def log_room_action(admin_user: User, action_type: str, room_obj, old_data: Dict = None, new_data: Dict = None, request=None):
        """Логирует действие с комнатой"""
        return AdminLogger.log_action(
            admin_user=admin_user,
            action_type=action_type,
            entity_type='room',
            entity_id=room_obj.room_id,
            entity_name=f"Комната {room_obj.room_id}",
            old_data=old_data,
            new_data=new_data,
            description=f"Действие с комнатой {room_obj.room_id}",
            request=request
        )


class AdminActionReverter:
    """Утилита для отката действий администраторов"""
    @staticmethod
    def revert_action(action_log: AdminActionLog, admin_user: User, reason: str = "") -> bool:
        """
        Откатывает действие администратора
        
        Args:
            action_log: Лог действия для отката
            admin_user: Администратор, выполняющий откат
            reason: Причина отката
            
        Returns:
            bool: True если откат успешен, False если нет
        """
        
        if not action_log.can_be_reverted():
            return False
        
        # Проверяем, не было ли уже создано записи об откате
        if hasattr(action_log, 'revert_record'):
            return False
        
        try:
            success = False
            error_message = ""
            
            # Выполняем откат в зависимости от типа действия
            if action_log.action_type == 'create':
                success = AdminActionReverter._revert_create(action_log)
            elif action_log.action_type == 'update':
                success = AdminActionReverter._revert_update(action_log)
            elif action_log.action_type == 'delete':
                success = AdminActionReverter._revert_delete(action_log)
            elif action_log.action_type == 'status_change':
                success = AdminActionReverter._revert_status_change(action_log)
            
            # Создаем запись об откате
            try:
                revert_record = AdminActionRevert.objects.create(
                    original_action=action_log,
                    reverted_by=admin_user,
                    revert_reason=reason,
                    revert_data=action_log.old_data,
                    success=success,
                    error_message=error_message
                )
            except Exception as revert_error:
                # Если запись отката уже существует, возвращаем False
                return False
            
            # Обновляем оригинальную запись
            if success:
                action_log.is_reverted = True
                action_log.reverted_at = timezone.now()
                action_log.reverted_by = admin_user
                action_log.revert_reason = reason
                action_log.save()
            
            return success
            
        except Exception as e:
            # Логируем ошибку только если записи отката еще нет
            try:
                if not hasattr(action_log, 'revert_record'):
                    AdminActionRevert.objects.create(
                        original_action=action_log,
                        reverted_by=admin_user,
                        revert_reason=reason,
                        success=False,
                        error_message=str(e)
                    )
            except:
                pass  # Игнорируем ошибки создания записи об ошибке
            return False

    @staticmethod
    def _revert_create(action_log: AdminActionLog) -> bool:
        """Откатывает создание объекта (удаляет его)"""
        try:
            if action_log.entity_type == 'user':
                user = User.objects.get(id=action_log.entity_id)
                user.delete()
                return True
            elif action_log.entity_type == 'news':
                from core.models import News
                news = News.objects.get(id=action_log.entity_id)
                news.delete()
                return True
            elif action_log.entity_type == 'comment':
                from core.models import Comment
                comment = Comment.objects.get(id=action_log.entity_id)
                comment.delete()
                return True
            # Добавить другие типы сущностей по необходимости
        except Exception:
            return False
        
        return False

    @staticmethod
    def _revert_update(action_log: AdminActionLog) -> bool:
        """Откатывает обновление объекта (восстанавливает старые данные)"""
        try:
            if action_log.entity_type == 'user':
                user = User.objects.get(id=action_log.entity_id)
                old_data = action_log.old_data
                
                # Восстанавливаем основные поля
                for field, value in old_data.items():
                    if hasattr(user, field) and field != 'password':  # Пароль не восстанавливаем
                        setattr(user, field, value)
                
                user.save()
                return True
                
            elif action_log.entity_type == 'news':
                from core.models import News
                news = News.objects.get(id=action_log.entity_id)
                old_data = action_log.old_data
                
                for field, value in old_data.items():
                    if hasattr(news, field):
                        setattr(news, field, value)
                
                news.save()
                return True
                
            elif action_log.entity_type == 'comment':
                from core.models import Comment
                comment = Comment.objects.get(id=action_log.entity_id)
                old_data = action_log.old_data
                  # Восстанавливаем только безопасные поля
                safe_fields = ['text', 'anime_id', 'likes_count']
                for field in safe_fields:
                    if field in old_data and hasattr(comment, field):
                        setattr(comment, field, old_data[field])
                
                comment.save()
                return True
            
        except Exception:
            return False
        
        return False

    @staticmethod
    def _revert_delete(action_log: AdminActionLog) -> bool:
        """Откатывает удаление объекта (восстанавливает его)"""
        try:
            old_data = action_log.old_data.copy()  # Создаем копию для безопасности
            
            if action_log.entity_type == 'user':
                # Восстанавливаем пользователя
                User.objects.create(**old_data)
                return True
                
            elif action_log.entity_type == 'news':
                from core.models import News
                News.objects.create(**old_data)
                return True
                
            elif action_log.entity_type == 'comment':
                from core.models import Comment
                
                # Подготавливаем данные для восстановления комментария
                comment_data = {
                    'anime_id': old_data['anime_id'],
                    'text': old_data['text'],
                    'likes_count': old_data.get('likes_count', 0)
                }
                
                # Восстанавливаем пользователя
                try:
                    user = User.objects.get(id=old_data['user_id'])
                    comment_data['user'] = user
                except User.DoesNotExist:
                    return False
                
                # Восстанавливаем родительский комментарий если есть
                if old_data.get('parent_id'):
                    try:
                        parent = Comment.objects.get(id=old_data['parent_id'])
                        comment_data['parent'] = parent
                    except Comment.DoesNotExist:
                        # Если родительский комментарий не найден, создаем без родителя
                        pass
                
                # Создаем комментарий с оригинальным ID если возможно
                try:
                    comment = Comment(**comment_data)
                    comment.pk = old_data['id']  # Пытаемся восстановить оригинальный ID
                    comment.save()
                except:
                    # Если не удается восстановить с оригинальным ID, создаем новый
                    Comment.objects.create(**comment_data)
                
                return True
            
        except Exception:
            return False
        
        return False

    @staticmethod
    def _revert_status_change(action_log: AdminActionLog) -> bool:
        """Откатывает изменение статуса"""
        return AdminActionReverter._revert_update(action_log)
