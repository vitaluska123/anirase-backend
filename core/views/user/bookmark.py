from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.models import Bookmark, BookmarkHistory

class BookmarkUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        anime_id = request.data.get('anime_id')
        status_value = request.data.get('status')
        watched_episodes = request.data.get('watched_episodes')
        if not anime_id or status_value not in ['watching', 'planned', 'completed', 'none']:
            return Response({'error': 'anime_id и status обязательны'}, status=400)
        if status_value == 'none':
            qs = Bookmark.objects.filter(user=user, anime_id=anime_id)
            if qs.exists():
                bm = qs.first()
                BookmarkHistory.objects.create(
                    user=user,
                    anime_id=anime_id,
                    status=bm.status,
                    watched_episodes=bm.watched_episodes,
                    event_type='remove',
                )
                qs.delete()
            return Response({'result': 'deleted'})
        prev = Bookmark.objects.filter(user=user, anime_id=anime_id).first()
        defaults = {'status': status_value}
        if watched_episodes is not None:
            try:
                defaults['watched_episodes'] = int(watched_episodes)
            except Exception:
                pass
        bookmark, created = Bookmark.objects.update_or_create(
            user=user, anime_id=anime_id,
            defaults=defaults
        )
        if created:
            BookmarkHistory.objects.create(
                user=user,
                anime_id=anime_id,
                status=status_value,
                watched_episodes=bookmark.watched_episodes,
                event_type='add',
            )
        else:
            if prev:
                if prev.status != status_value:
                    BookmarkHistory.objects.create(
                        user=user,
                        anime_id=anime_id,
                        status=status_value,
                        watched_episodes=bookmark.watched_episodes,
                        event_type='status',
                    )
                if watched_episodes is not None and prev.watched_episodes != bookmark.watched_episodes:
                    BookmarkHistory.objects.create(
                        user=user,
                        anime_id=anime_id,
                        status=status_value,
                        watched_episodes=bookmark.watched_episodes,
                        event_type='episodes',
                    )
        return Response({'result': 'ok', 'status': status_value, 'watched_episodes': bookmark.watched_episodes})
