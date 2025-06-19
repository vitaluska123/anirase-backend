# Получить текущую активную скидку
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import models
from django.utils import timezone
from core.models import Discount
from core.serializers import ProductListSerializer, DiscountSerializer

__all__ = ['CurrentDiscountView']

class CurrentDiscountView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        now = timezone.now()
        current_discount = Discount.objects.filter(
            start_date__lte=now,
            end_date__gte=now,
            is_active=True,
            activations_used__lt=models.F('max_activations')
        ).select_related('product').first()
        if current_discount:
            product_data = ProductListSerializer(
                current_discount.product, 
                context={'request': request}
            ).data
            discount_data = DiscountSerializer(
                current_discount,
                context={'request': request}
            ).data
            return Response({
                'product': product_data,
                'discount': discount_data
            })
        return Response({'product': None, 'discount': None})
