# Получение списка способов оплаты
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import PaymentMethod, ShopSettings
from core.serializers import PaymentMethodSerializer, ShopSettingsSerializer

__all__ = ['PaymentMethodsView']

class PaymentMethodsView(APIView):
    """
    Возвращает список доступных способов оплаты и настройки магазина
    """
    
    def get(self, request):
        # Получаем настройки магазина
        shop_settings = ShopSettings.objects.first()
        if not shop_settings:
            # Создаем настройки по умолчанию если их нет
            shop_settings = ShopSettings.objects.create()
        
        # Проверяем включена ли оплата
        if not shop_settings.payments_enabled:
            return Response({
                'payments_enabled': False,
                'message': shop_settings.maintenance_message,
                'payment_methods': []
            })
        
        # Получаем активные способы оплаты
        payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('sort_order')
        
        return Response({
            'payments_enabled': True,
            'message': None,
            'payment_methods': PaymentMethodSerializer(
                payment_methods, 
                many=True, 
                context={'request': request}
            ).data
        })
