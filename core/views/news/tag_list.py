from rest_framework import generics
from rest_framework.permissions import AllowAny
from core.models import Tag
from core.serializers import TagSerializer

__all__ = ['TagListView']

class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
