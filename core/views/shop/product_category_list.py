# Список категорий товаров
from rest_framework import generics
from rest_framework.permissions import AllowAny
from core.models import ProductCategory
from core.serializers import ProductCategorySerializer

__all__ = ['ProductCategoryListView']

class ProductCategoryListView(generics.ListAPIView):
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer
    permission_classes = [AllowAny]
