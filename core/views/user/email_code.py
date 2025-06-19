from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
import random
from django.conf import settings

class SendEmailCodeView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email обязателен'}, status=400)
        code = ''.join(random.choices('0123456789', k=6))
        cache.set(f'reg_code_{email}', code, timeout=15*60)
        try:
            html_message = render_to_string('core/email_verification.html', {'code': code})
            plain_message = render_to_string('core/email_verification.txt', {'code': code})
            send_mail(
                'Код подтверждения AniRase 🎌',
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
                html_message=html_message,
            )
        except Exception as e:
            return Response({'detail': f'Ошибка отправки письма: {e}'}, status=500)
        return Response({'detail': 'Код отправлен'})
