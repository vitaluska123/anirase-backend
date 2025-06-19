# Webhook RoboKassa
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import redirect
from core.models import Order
from core.utils.robokassa import verify_webhook_signature
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

__all__ = ['RoboKassaWebhookView']

class RoboKassaWebhookView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Обработка success/fail callback от RoboKassa (GET запросы)
        """
        out_sum = request.GET.get('OutSum')
        inv_id = request.GET.get('InvId')
        signature_value = request.GET.get('SignatureValue')
        
        logger.info(f"RoboKassa GET callback: OutSum={out_sum}, InvId={inv_id}, Signature={signature_value}")
        
        if not out_sum or not inv_id or not signature_value:
            logger.error("RoboKassa callback: missing parameters")
            return redirect(f"{settings.SITE_URL}/shop/payment-fail?error=invalid_params")
        
        # Проверяем подпись для success callback
        password1 = settings.ROBOKASSA_PASSWORD1
        if not verify_webhook_signature(out_sum, inv_id, signature_value, password1):
            logger.error(f"RoboKassa callback: invalid signature for order {inv_id}")
            return redirect(f"{settings.SITE_URL}/shop/payment-fail?order_id={inv_id}&error=invalid_signature")
        
        try:
            order = Order.objects.get(id=inv_id)
            logger.info(f"RoboKassa success callback for order {inv_id}")
            return redirect(f"{settings.SITE_URL}/shop/payment-success?order_id={inv_id}&status=success")
        except Order.DoesNotExist:
            logger.error(f"RoboKassa callback: order {inv_id} not found")
            return redirect(f"{settings.SITE_URL}/shop/payment-fail?order_id={inv_id}&error=order_not_found")
    
    def post(self, request):
        # Получаем данные от RoboKassa
        out_sum = request.data.get('OutSum')
        inv_id = request.data.get('InvId')
        signature_value = request.data.get('SignatureValue')
        
        if not out_sum or not inv_id or not signature_value:
            return Response({'error': 'Некорректные параметры'}, status=400)        # Проверяем подпись (используем утилиту)
        password2 = settings.ROBOKASSA_PASSWORD2
        
        if not verify_webhook_signature(out_sum, inv_id, signature_value, password2):
            return Response({'error': 'Неверная подпись'}, status=403)
        
        try:
            order = Order.objects.get(id=inv_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=404)
        
        # Обновляем статус заказа
        if order.status == 'pending':
            order.status = 'paid'
            order.save()
            
            # Выдача цифрового товара (аналогично AnyPay)
            if order.product.slug == 'premium':
                profile = order.user.profile
                profile.group_id = 3  # ID группы "Премиум"
                profile.save()
            elif order.product.slug.startswith('theme-'):
                profile = order.user.profile
                themes = profile.features.get('themes', [])
                if order.product.slug not in themes:
                    themes.append(order.product.slug)
                    profile.features['themes'] = themes
                    profile.save()
        
        return Response({'result': 'OK'})
