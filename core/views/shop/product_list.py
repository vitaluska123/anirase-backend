# Список товаров с фильтрацией по категориям
from rest_framework import generics
from rest_framework.permissions import AllowAny
from core.models import Product
from core.serializers import ProductListSerializer

__all__ = ['ProductListView']

class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        queryset = Product.objects.filter(is_published=True)
        category_slug = self.request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        return queryset.distinct()
