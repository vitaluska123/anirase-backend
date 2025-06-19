from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.crypto import get_random_string
from rest_framework import status
from core.models import Room
from django.contrib.auth import get_user_model

User = get_user_model()

class WatchRoomCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        anime_id = data.get('anime_id')
        is_private = bool(data.get('isPrivate', True))
        allow_control = bool(data.get('allowControl', False))
        if not anime_id:
            return Response({'error': 'anime_id required'}, status=status.HTTP_400_BAD_REQUEST)
        # Генерируем уникальный invite_code
        invite_code = get_random_string(16)
        # Создаём комнату в БД
        room = Room.objects.create(
            room_id=invite_code,
            anime_id=anime_id,
            is_private=is_private,
            allow_control=allow_control,
            host=request.user
        )
        return Response({'invite_code': room.room_id})

class PublicWatchRoomsView(APIView):
    def get(self, request):
        rooms = Room.objects.filter(is_private=False)
        data = [
            {
                'room_id': r.room_id,
                'anime_id': r.anime_id,
                'host': r.host.username if r.host else None,
                'allow_control': r.allow_control,
                'created': r.created_at.isoformat() if hasattr(r, 'created_at') else None,
            }
            for r in rooms
        ]
        return Response({'rooms': data})
