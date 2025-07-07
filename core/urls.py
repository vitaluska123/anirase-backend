from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import *
from .views.reports import report_admin_view
from .dashboard_urls import dashboard_urlpatterns

urlpatterns = [
    # --- Аутентификация ---
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/me/', UserProfileView.as_view(), name='current_user'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login_legacy'),  # Обратная совместимость
    path('send_email_code/', SendEmailCodeView.as_view(), name='send_email_code'),
    path('register_with_code/', RegisterWithCodeView.as_view(), name='register_with_code'),

    # --- Профиль пользователя ---
    path('history/', HistoryListCreateView.as_view(), name='history'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/avatar/', UserAvatarUpdateView.as_view(), name='profile_avatar'),
    path('public_user_info/', PublicUserInfoView.as_view(), name='public_user_info'),
    path('bookmark/', BookmarkUpdateView.as_view(), name='bookmark_update'),
    path('bookmark-history/', BookmarkHistoryView.as_view(), name='bookmark-history'),

    # --- Комментарии ---
    path('comments/', CommentView.as_view(), name='comments'),
    path('comments/<int:comment_id>/', CommentDetailView.as_view(), name='comment_detail'),

    # --- Новости и теги ---
    path('news/', NewsListView.as_view(), name='news_list'),
    path('news/<int:id>/', NewsDetailView.as_view(), name='news_detail'),
    path('tags/', TagListView.as_view(), name='tags_list'),

    # --- Интеграции ---
    path('shikimori/<path:endpoint>/', ShikimoriProxyView.as_view(), name='shikimori_proxy'),    # --- Магазин ---
    path('shop/categories/', ProductCategoryListView.as_view(), name='shop_categories'),
    path('shop/products/', ProductListView.as_view(), name='shop_products'),
    path('shop/products/<slug:slug>/', ProductDetailView.as_view(), name='shop_product_detail'),
    path('shop/current-discount/', CurrentDiscountView.as_view(), name='shop_current_discount'),    path('shop/payment-methods/', PaymentMethodsView.as_view(), name='shop_payment_methods'),
    path('shop/create-order/', CreateOrderView.as_view(), name='shop_create_order'),    path('shop/anypay-webhook/', AnyPayWebhookView.as_view(), name='shop_anypay_webhook'),
    path('shop/robokassa-webhook/', RoboKassaWebhookView.as_view(), name='shop_robokassa_webhook'),
    
    # --- Результаты платежей ---
    path('shop/payment-success/', PaymentSuccessView.as_view(), name='shop_payment_success'),
    path('shop/payment-fail/', PaymentFailView.as_view(), name='shop_payment_fail'),
    path('shop/payment-status/', PaymentStatusView.as_view(), name='shop_payment_status'),
    
    # --- Редиректы после платежа (GET запросы от RoboKassa) ---
    path('shop/payment-success-redirect/', PaymentSuccessRedirectView.as_view(), name='shop_payment_success_redirect'),
    path('shop/payment-fail-redirect/', PaymentFailRedirectView.as_view(), name='shop_payment_fail_redirect'),    # --- Генерация изображений для аниме ---
    path('generate/<int:idanime>/', AnimeImageGenerateView.as_view(), name='anime_image_generate'),
    path('watchroom/create/', WatchRoomCreateView.as_view(), name='watchroom_create'),
    path('watchroom/public/', PublicWatchRoomsView.as_view(), name='public_watch_rooms'),
]

# Добавляем dashboard URLs
urlpatterns += dashboard_urlpatterns
