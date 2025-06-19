# Создание заказа
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import requests
import hashlib
from core.models import Order, Product, PaymentMethod, ShopSettings
from core.serializers import CreateOrderSerializer
from core.utils.robokassa import generate_payment_signature, get_payment_url

__all__ = ['CreateOrderView']

class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Проверяем включена ли оплата
        shop_settings = ShopSettings.objects.first()
        if shop_settings and not shop_settings.payments_enabled:
            return Response({
                'error': shop_settings.maintenance_message or 'Оплата временно отключена'
            }, status=503)
        
        # Валидируем данные
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=400)
        
        product_id = serializer.validated_data['product_id']
        payment_method_id = serializer.validated_data['payment_method_id']
        
        try:
            product = Product.objects.get(id=product_id, is_published=True)
            payment_method = PaymentMethod.objects.get(id=payment_method_id, is_active=True)
        except (Product.DoesNotExist, PaymentMethod.DoesNotExist) as e:
            return Response({'error': 'Товар или способ оплаты не найден'}, status=404)
        
        amount = float(product.discounted_price)
          # Создаем заказ
        order = Order.objects.create(
            user=request.user,
            product=product,
            payment_method=payment_method,
            amount=amount,
            status='pending',
        )
        
        # Обрабатываем разные типы оплаты
        if payment_method.processor_type == 'anypay':
            return self._process_anypay_payment(order, product, amount, request)
        elif payment_method.processor_type == 'robokassa':
            return self._process_robokassa_payment(order, product, amount, request)
        elif payment_method.processor_type == 'manual':
            return self._process_manual_payment(order, product, amount)
        elif payment_method.processor_type == 'crypto':
            return self._process_crypto_payment(order, product, amount)
        elif payment_method.processor_type == 'bank':
            return self._process_bank_payment(order, product, amount)
        else:
            order.status = 'failed'
            order.save()
            return Response({'error': 'Неподдерживаемый способ оплаты'}, status=400)
    
    def _process_anypay_payment(self, order, product, amount, request):
        """Обработка платежа через AnyPay"""
        anypay_api_key = settings.ANYPAY_API_KEY
        anypay_shop_id = settings.ANYPAY_SHOP_ID
        pay_data = {
            'shop_id': anypay_shop_id,
            'amount': str(amount),
            'order_id': str(order.id),
            'currency': 'RUB',
            'desc': f'AniRase: {product.title}',
            'success_url': settings.SITE_URL + '/api/shop/payment-success/?order_id=' + str(order.id),
            'fail_url': settings.SITE_URL + '/api/shop/payment-fail/?order_id=' + str(order.id),
            'email': request.user.email or '',
        }
        
        headers = {'Authorization': f'Bearer {anypay_api_key}'}
        resp = requests.post('https://anypay.io/api/v2/invoice/create', json=pay_data, headers=headers)
        
        if resp.status_code != 200:
            order.status = 'failed'
            order.save()
            return Response({'error': 'Ошибка создания счёта AnyPay'}, status=500)
        invoice = resp.json().get('invoice')
        order.anypay_invoice_id = invoice['id']
        order.save()
        return Response({
            'order_id': order.id,
            'payment_type': 'redirect',
            'pay_url': invoice['pay_url']
        })    
    def _process_robokassa_payment(self, order, product, amount, request):
        """Обработка платежа через RoboKassa"""
        login = settings.ROBOKASSA_LOGIN
        password1 = settings.ROBOKASSA_PASSWORD1
        test_mode = settings.ROBOKASSA_TEST_MODE
        
        # Генерируем подпись для RoboKassa (используем утилиту)
        signature = generate_payment_signature(login, amount, order.id, password1)
        
        # Формируем URL для оплаты с success/fail редиректами
        # Для POST запросов (Result URL) - обработка платежей
        success_url = settings.SITE_URL + '/api/shop/payment-success/'
        fail_url = settings.SITE_URL + '/api/shop/payment-fail/'
        
        # Для GET запросов (Success/Fail URL) - редиректы пользователя
        success_redirect_url = settings.SITE_URL + '/api/shop/payment-success-redirect/'
        fail_redirect_url = settings.SITE_URL + '/api/shop/payment-fail-redirect/'
        
        pay_url = get_payment_url(
            login=login,
            amount=amount,
            order_id=order.id,
            signature=signature,
            description=f'AniRase: {product.title}',
            email=request.user.email or '',
            test_mode=test_mode,
            success_url=success_redirect_url,
            fail_url=fail_redirect_url
        )
        
        return Response({
            'order_id': order.id,
            'payment_type': 'redirect',
            'pay_url': pay_url
        })
    
    def _process_manual_payment(self, order, product, amount):
        """Обработка ручной оплаты"""
        return Response({
            'order_id': order.id,
            'payment_type': 'manual',
            'message': f'Заказ #{order.id} создан. Для оплаты свяжитесь с администрацией.',
            'contact_info': {
                'email': 'support@anirase.ru',
                'telegram': '@anirase_official'
            }
        })
    
    def _process_crypto_payment(self, order, product, amount):
        """Обработка криптоплатежа"""
        # Здесь можно интегрировать криптопроцессор
        return Response({
            'order_id': order.id,
            'payment_type': 'crypto',
            'message': f'Заказ #{order.id} создан. Инструкции по криптооплате будут отправлены на email.',
            'wallet_info': {
                'btc': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                'eth': '0x742d35Cc6634C0532925a3b8D7389a57e2F4F99A',
                'usdt': 'TG3XXyExBkPp9nzdajDGFahC9nyv4UYRTx'
            }
        })
    
    def _process_bank_payment(self, order, product, amount):
        """Обработка банковского перевода"""
        return Response({
            'order_id': order.id,
            'payment_type': 'bank',
            'message': f'Заказ #{order.id} создан. Реквизиты для оплаты:',
            'bank_details': {
                'recipient': 'Кудряшов Виталий Александрович',
                'inn': '366232766177',
                'account': 'Уточните у администрации',
                'amount': amount,
                'purpose': f'Оплата заказа #{order.id} - {product.title}'
            }
        })
