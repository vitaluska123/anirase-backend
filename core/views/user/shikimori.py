from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.cache import cache
from django.utils.http import urlencode
import requests
import hashlib

class ShikimoriProxyView(APIView):
    permission_classes = []
    
    def _get_cache_key(self, endpoint, query_params):
        """Генерирует уникальный ключ кеша для запроса"""
        params_string = urlencode(sorted(query_params.items())) if query_params else ''
        cache_string = f"shikimori:{endpoint}:{params_string}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def get(self, request, endpoint):
        # Проверяем кеш
        cache_key = self._get_cache_key(endpoint, request.query_params)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return Response(cached_data['data'], status=cached_data['status'])
        
        url = f'https://shikimori.one/api/{endpoint}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AniRase/1.0; +https://anirase.ru/)',
            'Accept': 'application/json',
        }
        try:
            resp = requests.get(url, params=request.query_params, headers=headers, timeout=10)
            try:
                data = resp.json()
                
                # Кешируем успешные ответы на 1 день (86400 секунд)
                if resp.status_code == 200:
                    cache.set(cache_key, {
                        'data': data,
                        'status': resp.status_code
                    }, 86400)
                
                return Response(data, status=resp.status_code)
            except Exception:
                return Response({'error': 'Invalid JSON from Shikimori'}, status=502)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
