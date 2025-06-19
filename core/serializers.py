from rest_framework import serializers
from django.contrib.auth.models import User
from .models import History, UserProfile, Bookmark, Comment, News, Tag, NewsImage, BookmarkHistory, Product, ProductCategory, Discount, DiscountActivation, Order, PaymentMethod, ShopSettings
# Сериализаторы для магазина
from .models import Product, ProductCategory, Discount

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = History
        fields = ['id', 'anime_id', 'watched_at']

class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    group_color = serializers.SerializerMethodField()
    class Meta:
        model = UserProfile
        fields = ['avatar_url', 'group', 'group_color']

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_group(self, obj):
        return obj.group.name if obj.group else None

    def get_group_color(self, obj):
        if obj.group and hasattr(obj.group, 'color_profile') and obj.group.color_profile:
            return obj.group.color_profile.color
        return None

class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['anime_id', 'status', 'watched_episodes', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    replies = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    is_reply = serializers.ReadOnlyField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'anime_id', 'text', 'created_at', 'updated_at', 
            'parent', 'likes_count', 'replies', 'replies_count', 'is_reply'
        ]
        read_only_fields = ['user', 'likes_count', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        if obj.parent is None:  # Только для основных комментариев
            replies = obj.get_replies()
            return CommentSerializer(replies, many=True, context=self.context).data
        return []
    
    def get_replies_count(self, obj):
        if obj.parent is None:
            return obj.replies.count()
        return 0

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']

class NewsImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsImage
        fields = ['id', 'image_url', 'alt_text']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class NewsSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    banner_url = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    images = NewsImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = News
        fields = [
            'id', 'title', 'banner_url', 'content', 'excerpt', 
            'tags', 'images', 'author', 'is_published', 
            'created_at', 'updated_at'
        ]
    
    def get_banner_url(self, obj):
        request = self.context.get('request')
        if obj.banner and hasattr(obj.banner, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.banner.url)
            return obj.banner.url
        return None

class NewsListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка новостей"""
    author = serializers.StringRelatedField(read_only=True)
    banner_url = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = News
        fields = [
            'id', 'title', 'banner_url', 'excerpt', 
            'tags', 'author', 'created_at'
        ]
    
    def get_banner_url(self, obj):
        request = self.context.get('request')
        if obj.banner and hasattr(obj.banner, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.banner.url)
            return obj.banner.url
        return None

class BookmarkHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookmarkHistory
        fields = ['id', 'anime_id', 'status', 'watched_episodes', 'event_type', 'created_at']

# Сериализаторы для магазина
class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'slug', 'color', 'icon', 'order', 'is_active']

class DiscountSerializer(serializers.ModelSerializer):
    time_left = serializers.SerializerMethodField()
    is_active_now = serializers.SerializerMethodField()
    
    class Meta:
        model = Discount
        fields = [
            'id', 'title', 'percentage', 'start_date', 'end_date', 
            'max_activations', 'activations_used', 'is_active',
            'time_left', 'is_active_now'
        ]
    
    def get_time_left(self, obj):
        from django.utils import timezone
        now = timezone.now()
        if obj.end_date > now:
            delta = obj.end_date - now
            return {
                'days': delta.days,
                'hours': delta.seconds // 3600,
                'minutes': (delta.seconds % 3600) // 60,
                'total_seconds': delta.total_seconds()
            }
        return None
    
    def get_is_active_now(self, obj):
        from django.utils import timezone
        now = timezone.now()
        return (obj.start_date <= now <= obj.end_date and 
                obj.is_active and 
                obj.activations_used < obj.max_activations)

class ProductSerializer(serializers.ModelSerializer):
    categories = ProductCategorySerializer(many=True, read_only=True)
    current_discount = DiscountSerializer(read_only=True)
    discounted_price = serializers.ReadOnlyField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'description', 'short_description',
            'price', 'discounted_price', 'image_url', 'categories',
            'features', 'is_digital', 'stock_quantity',
            'is_published', 'is_featured', 'order',
            'current_discount', 'created_at', 'updated_at'
        ]
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class ProductListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка товаров"""
    categories = ProductCategorySerializer(many=True, read_only=True)
    current_discount = DiscountSerializer(read_only=True)
    discounted_price = serializers.ReadOnlyField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'short_description',
            'price', 'discounted_price', 'image_url', 'categories',
            'is_digital', 'is_featured', 'current_discount'
        ]
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class OrderSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'product', 'product_title', 'amount', 'status', 'created_at', 'updated_at', 'payment_id', 'anypay_invoice_id']

class PaymentMethodSerializer(serializers.ModelSerializer):
    icon_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'slug', 'description', 'icon_url', 'processor_type']
    
    def get_icon_url(self, obj):
        request = self.context.get('request')
        if obj.icon and hasattr(obj.icon, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.icon.url)
            return obj.icon.url
        return None

class ShopSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSettings
        fields = ['payments_enabled', 'maintenance_message']

class CreateOrderSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    payment_method_id = serializers.IntegerField()
    
    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value, is_published=True)
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Товар не найден или не опубликован")
    
    def validate_payment_method_id(self, value):
        try:
            payment_method = PaymentMethod.objects.get(id=value, is_active=True)
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Способ оплаты не найден или неактивен")
