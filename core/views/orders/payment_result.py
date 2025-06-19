"""
Обработка результатов платежей
"""
from django.shortcuts import redirect
from django.views import View
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.models import Order
from core.utils.robokassa import verify_result_signature
import logging

logger = logging.getLogger(__name__)

__all__ = ['PaymentSuccessView', 'PaymentFailView', 'PaymentStatusView']

@method_decorator(csrf_exempt, name='dispatch')
class PaymentSuccessView(View):
    """
    Обработка успешной оплаты
    """
    
    def post(self, request):
        # Получаем параметры из POST запроса
        order_id = request.POST.get('InvId') or request.POST.get('order_id')
        invoice_id = request.POST.get('InvId')
        out_sum = request.POST.get('OutSum')
        signature = request.POST.get('SignatureValue')
        
        logger.info(f"Payment success callback: order_id={order_id}, invoice_id={invoice_id}, amount={out_sum}")
        
        try:
            if order_id:
                order = Order.objects.get(id=order_id)
                
                # Проверяем подпись RoboKassa
                if signature and not self._verify_signature(order, out_sum, signature):
                    logger.error(f"Invalid signature for order {order_id}")
                    return HttpResponse('Invalid signature', status=400)
                
                # Если заказ еще не оплачен, отмечаем как оплаченный
                if order.status == 'pending':
                    order.status = 'paid'
                    order.save()
                    
                    # Выдача цифрового товара
                    self._process_digital_goods(order)
                    
                    logger.info(f"Order {order_id} marked as paid")
                
                # Возвращаем успешный ответ для RoboKassa
                return HttpResponse('OK')
            
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found in success callback")
            return HttpResponse('Order not found', status=404)
            
        return HttpResponse('Invalid request', status=400)
    
    def get(self, request):
        # Обработка GET запросов (редирект с фронтенда)
        order_id = request.GET.get('order_id')
        
        if order_id:
            # Редирект на фронтенд с параметрами успеха
            redirect_url = f"{settings.SITE_URL}/shop/payment-success?order_id={order_id}&status=success"
            return redirect(redirect_url)
        
        # Редирект на фронтенд с ошибкой
        redirect_url = f"{settings.SITE_URL}/shop/payment-success?status=error&message=order_not_found"
        return redirect(redirect_url)
    
    def _verify_signature(self, order, out_sum, signature):
        """
        Проверка подписи результата платежа
        """
        try:
            return verify_result_signature(
                out_sum=out_sum,
                inv_id=str(order.id),
                signature=signature
            )
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}")
            return False
    
    def _process_digital_goods(self, order):
        """
        Обработка выдачи цифровых товаров
        """
        try:
            user_profile = order.user.profile
            
            # Обработка премиум подписки
            if order.product.slug == 'premium':
                user_profile.group_id = 3  # ID группы "Премиум"
                user_profile.save()
                logger.info(f"Premium access granted to user {order.user.username}")
            
            # Обработка тем оформления
            elif order.product.slug.startswith('theme-'):
                features = user_profile.features or {}
                themes = features.get('themes', [])
                
                if order.product.slug not in themes:
                    themes.append(order.product.slug)
                    features['themes'] = themes
                    user_profile.features = features
                    user_profile.save()
                    logger.info(f"Theme {order.product.slug} granted to user {order.user.username}")
            
            # Обработка других цифровых товаров
            elif order.product.features:
                features = user_profile.features or {}
                product_features = order.product.features
                
                # Объединяем функции товара с профилем пользователя
                for key, value in product_features.items():
                    if key in features:
                        if isinstance(features[key], list) and isinstance(value, list):
                            features[key].extend(value)
                        else:
                            features[key] = value
                    else:
                        features[key] = value
                
                user_profile.features = features
                user_profile.save()
                logger.info(f"Digital goods from {order.product.slug} granted to user {order.user.username}")
                
        except Exception as e:
            logger.error(f"Error processing digital goods for order {order.id}: {str(e)}")


@method_decorator(csrf_exempt, name='dispatch')
class PaymentFailView(View):
    """
    Обработка неуспешной оплаты
    """
    
    def post(self, request):
        # Получаем параметры из POST запроса
        order_id = request.POST.get('InvId') or request.POST.get('order_id')
        invoice_id = request.POST.get('InvId')
        error_message = request.POST.get('error', 'payment_failed')
        
        logger.warning(f"Payment failed callback: order_id={order_id}, invoice_id={invoice_id}, error={error_message}")
        
        try:
            if order_id:
                order = Order.objects.get(id=order_id)
                
                # Отмечаем заказ как неуспешный, если он еще в статусе ожидания
                if order.status == 'pending':
                    order.status = 'failed'
                    order.save()
                    logger.info(f"Order {order_id} marked as failed")
                
                # Возвращаем ответ для RoboKassa
                return HttpResponse('OK')
            
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found in fail callback")
            return HttpResponse('Order not found', status=404)
            
        return HttpResponse('Invalid request', status=400)
    
    def get(self, request):
        # Обработка GET запросов (редирект с фронтенда)
        order_id = request.GET.get('order_id')
        error_message = request.GET.get('error', 'payment_failed')
        
        if order_id:
            # Редирект на фронтенд с параметрами ошибки
            redirect_url = f"{settings.SITE_URL}/shop/payment-fail?order_id={order_id}&status=failed&error={error_message}"
            return redirect(redirect_url)
        
        # Редирект на фронтенд с общей ошибкой
        redirect_url = f"{settings.SITE_URL}/shop/payment-fail?status=error&error=order_not_found"
        return redirect(redirect_url)


class PaymentStatusView(View):
    """
    API для проверки статуса платежа (AJAX запросы)
    """
    
    def get(self, request):
        order_id = request.GET.get('order_id')
        
        if not order_id:
            return HttpResponse('{"error": "order_id required"}', 
                              content_type='application/json', status=400)
        
        try:
            order = Order.objects.get(id=order_id)
            
            response_data = {
                'order_id': order.id,
                'status': order.status,
                'amount': str(order.amount),
                'product': order.product.title,
                'created_at': order.created_at.isoformat(),
            }
            
            if order.status == 'paid':
                response_data['message'] = 'Платеж успешно обработан'
            elif order.status == 'failed':
                response_data['message'] = 'Платеж не выполнен'
            else:
                response_data['message'] = 'Платеж в обработке'
            
            import json
            return HttpResponse(json.dumps(response_data), 
                              content_type='application/json')
            
        except Order.DoesNotExist:
            return HttpResponse('{"error": "Order not found"}', 
                              content_type='application/json', status=404)
