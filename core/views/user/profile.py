from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import UserProfile, Bookmark, History
from core.serializers import UserProfileSerializer, BookmarkSerializer, HistorySerializer

class UserProfileView(APIView):
    def get(self, request):
        username = request.query_params.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
                profile = user.profile
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                return Response({'error': 'Пользователь не найден'}, status=404)
            profile_data = UserProfileSerializer(profile, context={'request': request}).data
            return Response({
                'id': user.id,
                'username': user.username,
                'avatar_url': profile_data['avatar_url'],
                'group': profile_data['group'],
                'group_color': profile_data['group_color'],
            })
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        user = request.user
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)
        profile_data = UserProfileSerializer(profile, context={'request': request}).data
        bookmarks = Bookmark.objects.filter(user=user)
        bookmarks_by_status = {'watching': [], 'planned': [], 'completed': []}
        for bm in bookmarks:
            bookmarks_by_status[bm.status].append(BookmarkSerializer(bm).data)
        history = History.objects.filter(user=user).order_by('-watched_at')[:30]
        history_data = HistorySerializer(history, many=True).data
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'avatar_url': profile_data['avatar_url'],
            'group': profile_data['group'],
            'group_color': profile_data['group_color'],
            'bookmarks': bookmarks_by_status,
            'history': history_data,
        })
