from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from core.models import UserProfile
from core.serializers import UserProfileSerializer

class PublicUserInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        username = request.query_params.get('username')
        if not username:
            return Response({'error': 'username required'}, status=400)
        try:
            user = User.objects.get(username=username)
            profile = user.profile
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            return Response({'error': 'Пользователь не найден'}, status=404)
        profile_data = UserProfileSerializer(profile, context={'request': request}).data
        return Response({
            'avatar_url': profile_data['avatar_url'],
            'group': profile_data['group'],
            'group_color': profile_data['group_color'],
        })
