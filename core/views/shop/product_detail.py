# Детальная информация о товаре
from rest_framework import generics
from rest_framework.permissions import AllowAny
from core.models import Product
from core.serializers import ProductSerializer

__all__ = ['ProductDetailView']

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_published=True)
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]
