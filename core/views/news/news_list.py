from rest_framework import generics
from rest_framework.permissions import AllowAny
from core.models import News
from core.serializers import NewsListSerializer

__all__ = ['NewsListView']

class NewsListView(generics.ListAPIView):
    serializer_class = NewsListSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        return News.objects.filter(is_published=True).order_by('-created_at')
