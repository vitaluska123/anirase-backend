from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from core.models import Comment
from core.serializers import CommentSerializer

__all__ = [
    'CommentView',
    'CommentDetailView',
]

class CommentView(APIView):
    def get(self, request):
        anime_id = request.query_params.get('anime_id')
        if not anime_id:
            return Response({'error': 'anime_id required'}, status=400)
        
        # Получаем только основные комментарии (без parent)
        comments = Comment.objects.filter(
            anime_id=anime_id, 
            parent__isnull=True
        ).prefetch_related('replies__user').order_by('-created_at')[:50]
        
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        anime_id = request.data.get('anime_id')
        text = request.data.get('text')
        parent_id = request.data.get('parent_id')  # Для ответов
        
        if not anime_id or not text:
            return Response({'error': 'anime_id и text обязательны'}, status=400)
        
        # Проверяем parent комментарий, если указан
        parent_comment = None
        if parent_id:
            try:
                parent_comment = Comment.objects.get(id=parent_id, anime_id=anime_id)
                if parent_comment.parent is not None:
                    # Не разрешаем ответы на ответы (только 2 уровня)
                    return Response({'error': 'Нельзя отвечать на ответы'}, status=400)
            except Comment.DoesNotExist:
                return Response({'error': 'Родительский комментарий не найден'}, status=400)
        
        comment = Comment.objects.create(
            user=request.user, 
            anime_id=anime_id, 
            text=text,
            parent=parent_comment
        )
        
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=201)
