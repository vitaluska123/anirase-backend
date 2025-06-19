from rest_framework import generics
from rest_framework.permissions import AllowAny
from core.models import News
from core.serializers import NewsSerializer

__all__ = ['NewsDetailView']

class NewsDetailView(generics.RetrieveAPIView):
    serializer_class = NewsSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'
    def get_queryset(self):
        return News.objects.filter(is_published=True)
