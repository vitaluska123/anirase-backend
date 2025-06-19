# __init__.py для core/views/
# Здесь импортируются все view-классы и функции для экспорта

from .shop import *
from .user import *
from .news import *
from .comments import *
from .discounts import *
from .orders import *
from .admin_stats import *
from .anime_image import AnimeImageGenerateView
from .watchroom import WatchRoomCreateView, PublicWatchRoomsView
# ...добавляйте новые модули по мере необходимости
