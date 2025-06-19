from django.contrib.auth.models import User, Group
from django.db import models
from mdeditor.fields import MDTextField

class GroupColor(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='color_profile')
    color = models.CharField(max_length=16, blank=True, null=True, help_text='HEX или CSS-цвет для бейджа')

    def __str__(self):
        return f"{self.group.name} ({self.color})"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')

    def __str__(self):
        return f"Profile: {self.user.username}"

class Bookmark(models.Model):
    STATUS_CHOICES = [
        ('watching', 'Смотрю'),
        ('planned', 'Запланировано'),
        ('completed', 'Просмотрено'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    anime_id = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    watched_episodes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'anime_id', 'status')

    def __str__(self):
        return f"{self.user.username} - {self.anime_id} ({self.status}) [{self.watched_episodes}]"

class History(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history')
    anime_id = models.CharField(max_length=255)
    watched_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.anime_id} ({self.watched_at})"

class Room(models.Model):
    room_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Новые поля для совместного просмотра
    is_private = models.BooleanField(default=True)
    allow_control = models.BooleanField(default=False)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms', null=True)
    anime_id = models.CharField(max_length=255, default="unknown")

    def __str__(self):
        return self.room_id

class RoomSession(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=255)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.room.room_id} - {self.session_key}"

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    anime_id = models.CharField(max_length=255)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Система ответов
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Статистика
    likes_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['anime_id', '-created_at']),
            models.Index(fields=['parent', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.anime_id}): {self.text[:30]}"
    
    @property
    def is_reply(self):
        return self.parent is not None
    
    def get_replies(self):
        return self.replies.filter(parent=self).order_by('created_at')

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название тега")
    color = models.CharField(max_length=7, default="#007bff", verbose_name="Цвет тега")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name

class News(models.Model):
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    banner = models.ImageField(upload_to='news/banners/', blank=True, null=True, verbose_name="Баннер")
    content = MDTextField(verbose_name="Содержание (Markdown)")
    excerpt = models.TextField(max_length=300, blank=True, verbose_name="Краткое описание")
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Теги")
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Автоматически создаем краткое описание если не указано
        if not self.excerpt and self.content:
            # Убираем markdown разметку для превью
            import re
            plain_text = re.sub(r'[#*`\[\]()]', '', self.content)
            self.excerpt = plain_text[:300] + '...' if len(plain_text) > 300 else plain_text
        super().save(*args, **kwargs)

class NewsImage(models.Model):
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name='images', verbose_name="Новость")
    image = models.ImageField(upload_to='news/images/', verbose_name="Изображение")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="Альтернативный текст")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Изображение новости"
        verbose_name_plural = "Изображения новостей"

    def __str__(self):
        return f"Изображение для: {self.news.title}"

class BookmarkHistory(models.Model):
    EVENT_CHOICES = [
        ('add', 'Добавление'),
        ('remove', 'Удаление'),
        ('status', 'Смена статуса'),
        ('episodes', 'Изменение серий'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmark_history')
    anime_id = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Bookmark.STATUS_CHOICES)
    watched_episodes = models.PositiveIntegerField(default=0)
    event_type = models.CharField(max_length=16, choices=EVENT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'История закладок'
        verbose_name_plural = 'История закладок'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.anime_id} [{self.event_type}] ({self.status}, {self.watched_episodes})"

# Модели магазина
class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL slug")
    color = models.CharField(max_length=7, default="#007bff", verbose_name="Цвет категории")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Иконка (emoji или класс)")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Категория товаров"
        verbose_name_plural = "Категории товаров"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class Product(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название товара")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL slug")
    description = MDTextField(verbose_name="Описание товара (Markdown)")
    short_description = models.TextField(max_length=300, blank=True, verbose_name="Краткое описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Изображение")
    categories = models.ManyToManyField(ProductCategory, blank=True, verbose_name="Категории")
    
    # Дополнительные поля для товара
    features = models.JSONField(default=dict, blank=True, verbose_name="Характеристики товара")
    is_digital = models.BooleanField(default=True, verbose_name="Цифровой товар")
    stock_quantity = models.PositiveIntegerField(default=999, verbose_name="Количество на складе")
    
    # Настройки публикации
    is_published = models.BooleanField(default=True, verbose_name="Опубликован")
    is_featured = models.BooleanField(default=False, verbose_name="Рекомендуемый")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['order', '-created_at']    
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Автоматически создаем краткое описание если не указано
        if not self.short_description and self.description:
            import re
            plain_text = re.sub(r'[#*`\[\]()]', '', self.description)
            self.short_description = plain_text[:300] + '...' if len(plain_text) > 300 else plain_text
        super().save(*args, **kwargs)

    @property
    def current_discount(self):
        """Получить текущую активную скидку"""
        from django.utils import timezone
        now = timezone.now()
        return self.discounts.filter(
            start_date__lte=now,
            end_date__gte=now,
            is_active=True,
            activations_used__lt=models.F('max_activations')
        ).first()

    @property
    def discounted_price(self):
        """Цена со скидкой"""
        from decimal import Decimal, ROUND_HALF_UP
        discount = self.current_discount
        if discount:
            discount_amount = self.price * (Decimal(str(discount.percentage)) / Decimal('100'))
            new_price = self.price - discount_amount
            return new_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return self.price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class Discount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='discounts', verbose_name="Товар")
    title = models.CharField(max_length=200, verbose_name="Название скидки")
    percentage = models.PositiveIntegerField(verbose_name="Процент скидки (1-99)")
    start_date = models.DateTimeField(verbose_name="Дата начала")
    end_date = models.DateTimeField(verbose_name="Дата окончания")
    max_activations = models.PositiveIntegerField(default=1, verbose_name="Максимальное количество активаций")
    activations_used = models.PositiveIntegerField(default=0, verbose_name="Использовано активаций")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.title} - {self.percentage}% ({self.product.title})"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        # Проверяем, что процент скидки в допустимых пределах
        if not (1 <= self.percentage <= 99):
            raise ValidationError("Процент скидки должен быть от 1 до 99")
        
        # Проверяем, что дата окончания больше даты начала
        if self.end_date <= self.start_date:
            raise ValidationError("Дата окончания должна быть больше даты начала")
        
        # Проверяем пересечения с другими скидками на тот же товар
        overlapping_discounts = Discount.objects.filter(
            product=self.product,
            is_active=True
        ).exclude(pk=self.pk if self.pk else None)
        
        for discount in overlapping_discounts:
            # Проверяем пересечение дат
            if (self.start_date < discount.end_date and self.end_date > discount.start_date):
                raise ValidationError(
                    f"Скидка пересекается по времени с существующей скидкой: {discount.title}"
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class DiscountActivation(models.Model):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='activations', verbose_name="Скидка")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discount_activations', verbose_name="Пользователь")
    activated_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата активации")
    order_id = models.CharField(max_length=100, blank=True, verbose_name="ID заказа")

    class Meta:
        verbose_name = "Активация скидки"
        verbose_name_plural = "Активации скидок"
        unique_together = ['discount', 'user']
        ordering = ['-activated_at']

    def __str__(self):
        return f"{self.user.username} - {self.discount.title}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидание оплаты'),
        ('paid', 'Оплачено'),
        ('failed', 'Ошибка оплаты'),
        ('cancelled', 'Отменён'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='orders')
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Способ оплаты")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_id = models.CharField(max_length=128, blank=True, null=True)
    anypay_invoice_id = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.product.title} ({self.status})"

class EmailAccount(models.Model):
    name = models.CharField(max_length=64, help_text='Название ящика (для отображения)')
    email = models.EmailField(unique=True)
    imap_server = models.CharField(max_length=128, default='imap.mail.ru')
    imap_port = models.PositiveIntegerField(default=993)
    smtp_server = models.CharField(max_length=128, default='smtp.mail.ru')
    smtp_port = models.PositiveIntegerField(default=465)
    username = models.CharField(max_length=128)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"


# Модели для способов оплаты
class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название способа оплаты")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Идентификатор")
    icon = models.ImageField(upload_to='payment_methods/', blank=True, null=True, verbose_name="Иконка")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")
    processor_type = models.CharField(max_length=50, choices=[
        ('anypay', 'AnyPay'),
        ('robokassa', 'RoboKassa'),
        ('manual', 'Ручная обработка'),
        ('crypto', 'Криптовалюта'),
        ('bank', 'Банковский перевод'),
    ], default='anypay', verbose_name="Тип обработчика")
    processor_config = models.JSONField(default=dict, blank=True, verbose_name="Настройки обработчика")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Способ оплаты"
        verbose_name_plural = "Способы оплаты"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ShopSettings(models.Model):
    """Настройки магазина (синглтон)"""
    payments_enabled = models.BooleanField(default=True, verbose_name="Оплата включена")
    maintenance_message = models.TextField(
        blank=True, 
        verbose_name="Сообщение при отключенной оплате",
        default="Оплата временно отключена. Попробуйте позже."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки магазина"
        verbose_name_plural = "Настройки магазина"

    def __str__(self):
        return "Настройки магазина"

    def save(self, *args, **kwargs):
        # Обеспечиваем, что существует только одна запись настроек
        if not self.pk and ShopSettings.objects.exists():
            raise ValueError("Настройки магазина уже существуют. Можно редактировать только существующие.")
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Получить настройки магазина (создать если не существуют)"""
        settings, created = cls.objects.get_or_create(defaults={
            'payments_enabled': True,
            'maintenance_message': 'Оплата временно отключена. Попробуйте позже.'
        })
        return settings
