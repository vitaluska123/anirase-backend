# middleware/dashboard_auth.py
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.request import Request
import json

class DashboardStaffRequiredMiddleware(MiddlewareMixin):
    """
    Middleware для проверки staff статуса для всех dashboard эндпоинтов
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Проверяем, относится ли запрос к dashboard API
        if request.path.startswith('/api/dashboard/'):
            # Используем JWT аутентификацию для получения пользователя
            jwt_auth = JWTAuthentication()
            try:
                # Пытаемся аутентифицировать пользователя через JWT
                auth_result = jwt_auth.authenticate(request)
                if auth_result is None:
                    return JsonResponse({
                        'error': 'Authentication required',
                        'message': 'Необходима аутентификация для доступа к панели администратора'
                    }, status=401)
                
                user, token = auth_result
                request.user = user
                
                # Проверяем staff статус
                if not user.is_staff:
                    return JsonResponse({
                        'error': 'Access denied',
                        'message': 'Доступ к панели администратора разрешен только для сотрудников'
                    }, status=403)
                    
            except Exception as e:
                return JsonResponse({
                    'error': 'Authentication failed',
                    'message': 'Токен недействителен или истек'
                }, status=401)
        
        return None
