from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from core.models import BookmarkHistory
from core.serializers import BookmarkHistorySerializer
from django.contrib.auth.models import User
from rest_framework.exceptions import NotFound

class BookmarkHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        username = request.GET.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise NotFound('Пользователь не найден')
            qs = BookmarkHistory.objects.filter(user=user).order_by('-created_at')[:200]
        else:
            if not request.user.is_authenticated:
                return Response({'detail': 'Требуется авторизация'}, status=401)
            qs = BookmarkHistory.objects.filter(user=request.user).order_by('-created_at')[:200]
        serializer = BookmarkHistorySerializer(qs, many=True)
        return Response(serializer.data)
    def get_permissions(self):
        if self.request.GET.get('username'):
            return [AllowAny()]
        return [IsAuthenticated()]
