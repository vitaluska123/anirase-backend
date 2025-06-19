"""
View для обработки редиректов после платежа
"""
from django.shortcuts import redirect
from django.views import View
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class PaymentSuccessRedirectView(View):
    """
    Обработка редиректа после успешной оплаты (GET запрос)
    """
    
    def get(self, request):
        order_id = request.GET.get('InvId') or request.GET.get('order_id')
        out_sum = request.GET.get('OutSum')
        
        logger.info(f"Payment success redirect: order_id={order_id}, amount={out_sum}")
        
        if order_id:
            redirect_url = f"{settings.SITE_URL}/shop/payment-success?order_id={order_id}&status=success"
        else:
            redirect_url = f"{settings.SITE_URL}/shop/payment-success?status=error&message=order_not_found"
        
        return redirect(redirect_url)


class PaymentFailRedirectView(View):
    """
    Обработка редиректа после неуспешной оплаты (GET запрос)
    """
    
    def get(self, request):
        order_id = request.GET.get('InvId') or request.GET.get('order_id')
        
        logger.warning(f"Payment fail redirect: order_id={order_id}")
        
        if order_id:
            redirect_url = f"{settings.SITE_URL}/shop/payment-fail?order_id={order_id}&status=failed"
        else:
            redirect_url = f"{settings.SITE_URL}/shop/payment-fail?status=error&error=order_not_found"
        
        return redirect(redirect_url)
