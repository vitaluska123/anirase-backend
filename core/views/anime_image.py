import io
import requests
from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View
from PIL import Image, ImageDraw, ImageFont
import textwrap

# Реальный запрос к Shikimori API
def get_anime_info(anime_id):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AniRase/1.0; +https://anirase.ru/)',
            'Accept': 'application/json',
        }
        response = requests.get(f'https://shikimori.one/api/animes/{anime_id}',headers=headers)
        response.raise_for_status()
        data = response.json()
        return {
            'title': data.get('russian') or data.get('name') or f'Аниме #{anime_id}',
            'orig_title': data.get('name', ''),
            'score': str(data.get('score', '—')),
            'image_url': 'https://shikimori.one' + data['image']['original'] if data.get('image') and data['image'].get('original') else '',
            'year': str(data.get('aired_on', '')[:4]) if data.get('aired_on') else '',
            'type': {
                'tv': 'TV Сериал',
                'movie': 'Фильм',
                'ova': 'OVA',
                'ona': 'ONA',
                'special': 'Спешл',
                'music': 'Клип'
            }.get(data.get('kind', ''), data.get('kind', '').upper()),
            'description': data.get('description', '') or 'Описание недоступно.'
        }
    except Exception as e:
        return {
            'title': f'Ошибка: {str(e)}',
            'orig_title': '',
            'score': '—',
            'image_url': '',
            'year': '',
            'type': '',
            'description': 'Описание недоступно.'
        }

class AnimeImageGenerateView(View):
    def get(self, request, idanime):
        info = get_anime_info(idanime)
        if not info:
            return HttpResponseBadRequest('Аниме не найдено')
        # Скачиваем обложку
        try:
            img_response = requests.get(info['image_url'])
            img_response.raise_for_status()
            cover = Image.open(io.BytesIO(img_response.content)).convert('RGBA')
        except Exception:
            cover = Image.new('RGBA', (300, 420), (200, 200, 200, 255))
        # Создаём фон
        width, height = 800, 420
        bg = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(bg)
        # Градиент
        for y in range(height):
            r = int(40 + 80 * y / height)
            g = int(60 + 100 * y / height)
            b = int(120 + 100 * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        # Вставляем обложку
        cover = cover.resize((300, 420))
        bg.paste(cover, (0, 0), cover)
        # Текст
        font_title = ImageFont.truetype("arial.ttf", 32)
        font_score = ImageFont.truetype("arial.ttf", 28)
        font_site = ImageFont.truetype("arial.ttf", 22)
        # --- Перенос длинного названия ---
        max_width = 440
        title = info['title']
        lines = []
        words = title.split()
        line = ''
        for word in words:
            test_line = (line + ' ' + word).strip()
            bbox = font_title.getbbox(test_line)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                line = test_line
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        # Ограничим до 2 строк, если больше — добавим ...
        if len(lines) > 2:
            lines = lines[:2]
            # Добавим ... к последней строке
            while (font_title.getbbox(lines[1] + '...')[2] - font_title.getbbox(lines[1] + '...')[0]) > max_width and len(lines[1]) > 0:
                lines[1] = lines[1][:-1]
            lines[1] = lines[1].rstrip() + '...'
        # Рисуем название
        y_title = 40
        for l in lines:
            draw.text((320, y_title), l, font=font_title, fill=(255,255,255,255))
            bbox = font_title.getbbox(l)
            h = bbox[3] - bbox[1]
            y_title += h + 4
        # Рейтинг и AniRase.ru как было
        draw.text((320, 100 + (y_title-40)), f"Рейтинг: {info['score']}", font=font_score, fill=(255,255,180,255))
        draw.text((320, 380), "AniRase.ru", font=font_site, fill=(255,255,255,255))
        # Сохраняем в память
        output = io.BytesIO()
        bg.save(output, format='PNG')
        output.seek(0)
        return HttpResponse(output, content_type='image/png')
