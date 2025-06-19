from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from core.models import Comment
from core.serializers import CommentSerializer

__all__ = ['CommentDetailView']

class CommentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        if comment.user != request.user:
            return Response({'error': 'У вас нет прав на редактирование этого комментария'}, status=403)
        text = request.data.get('text')
        if not text or not text.strip():
            return Response({'error': 'Текст комментария не может быть пустым'}, status=400)
        comment.text = text.strip()
        comment.save()
        serializer = CommentSerializer(comment)
        return Response(serializer.data)
    def delete(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        if comment.user != request.user:
            return Response({'error': 'У вас нет прав на удаление этого комментария'}, status=403)
        comment.delete()
        return Response({'result': 'deleted'})
