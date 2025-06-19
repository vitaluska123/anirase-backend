from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

class RegisterWithCodeView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        password2 = request.data.get('password2')
        email = request.data.get('email')
        code = request.data.get('code')
        if not all([username, password, password2, email, code]):
            return Response({'detail': 'Все поля обязательны'}, status=400)
        if password != password2:
            return Response({'detail': 'Пароли не совпадают'}, status=400)
        cached_code = cache.get(f'reg_code_{email}')
        if not cached_code or cached_code != code:
            return Response({'detail': 'Неверный или просроченный код'}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({'detail': 'Пользователь с таким именем уже существует'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'detail': 'Пользователь с такой почтой уже существует'}, status=400)
        user = User.objects.create_user(username=username, email=email, password=password)
        cache.delete(f'reg_code_{email}')
        return Response({'detail': 'Регистрация успешна'})
