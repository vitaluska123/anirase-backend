# Webhook AnyPay
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from core.models import Order
import hashlib
from django.conf import settings

__all__ = ['AnyPayWebhookView']

class AnyPayWebhookView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        invoice_id = request.data.get('invoice_id')
        status_pay = request.data.get('status')
        order_id = request.data.get('order_id')
        sign = request.data.get('sign')
        # Проверка подписи (MD5)
        if not invoice_id or not status_pay or not order_id or not sign:
            return Response({'error': 'Некорректные параметры'}, status=400)
        # Формируем строку для подписи по документации AnyPay
        # Обычно: f"{order_id}:{status_pay}:{settings.ANYPAY_API_KEY}"
        sign_str = f"{order_id}:{status_pay}:{settings.ANYPAY_API_KEY}"
        expected_sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        if sign != expected_sign:
            return Response({'error': 'Неверная подпись'}, status=403)
        try:
            order = Order.objects.get(id=order_id, anypay_invoice_id=invoice_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=404)
        if status_pay == 'paid':
            order.status = 'paid'
            order.save()
            # Выдача цифрового товара (пример: премиум, тема и т.д.)
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
        elif status_pay == 'cancelled':
            order.status = 'cancelled'
            order.save()
        elif status_pay == 'failed':
            order.status = 'failed'
            order.save()
        return Response({'result': 'ok'})
