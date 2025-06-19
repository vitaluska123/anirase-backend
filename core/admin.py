from django.contrib import admin
from django.contrib.auth.models import Group
from .models import History, Room, RoomSession, Bookmark, Comment, UserProfile, GroupColor, News, Tag, NewsImage, BookmarkHistory, Product, ProductCategory, Discount, DiscountActivation, Order, EmailAccount, PaymentMethod, ShopSettings
from mdeditor.widgets import MDEditorWidget
from django import forms
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import admin
from django.conf import settings
from django.contrib.admin.sites import NotRegistered

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime_id', 'status', 'watched_episodes', 'created_at')
    list_filter = ('status', 'user','anime_id')
    search_fields = ('anime_id', 'user__username')

admin.site.register(History)
admin.site.register(Room)
admin.site.register(RoomSession)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime_id', 'text', 'created_at')
    list_filter = ('user', 'anime_id')
    search_fields = ('anime_id', 'user__username', 'text')

class NewsImageInline(admin.TabularInline):
    model = NewsImage
    extra = 1
    fields = ('image', 'alt_text')

class NewsAdminForm(forms.ModelForm):
    class Meta:
        model = News
        fields = '__all__'
        widgets = {
            'content': MDEditorWidget(config_name='default', attrs={'style': 'height: 600px;'}),
            'excerpt': forms.Textarea(attrs={'rows': 4, 'style': 'resize:vertical;'}),
        }

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    form = NewsAdminForm
    list_display = ('title', 'is_published', 'created_at', 'updated_at')
    list_filter = ('is_published', 'tags', 'created_at')
    search_fields = ('title', 'content', 'excerpt')
    filter_horizontal = ('tags',)
    inlines = [NewsImageInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'banner', 'is_published')
        }),
        ('Содержание', {
            'fields': ('content',)
        }),
        ('Краткое описание', {
            'fields': ('excerpt',)
        }),
        ('Теги', {
            'fields': ('tags',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

@admin.register(BookmarkHistory)
class BookmarkHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime_id', 'event_type', 'status', 'watched_episodes', 'created_at')
    list_filter = ('event_type', 'status', 'user')
    search_fields = ('anime_id', 'user__username')
    ordering = ('-created_at',)

# Админка для магазина
from .models import Product, ProductCategory, Discount, DiscountActivation

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'description': MDEditorWidget(config_name='default', attrs={'style': 'height: 400px;'}),
            'short_description': forms.Textarea(attrs={'rows': 3, 'style': 'resize:vertical;'}),
            'features': forms.Textarea(attrs={'rows': 4, 'placeholder': 'JSON формат: {"ключ": "значение"}'}),
        }

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color', 'icon', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order', 'is_active')
    ordering = ('order', 'name')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('title', 'slug', 'price', 'is_digital', 'stock_quantity', 'is_published', 'is_featured', 'order')
    list_filter = ('is_published', 'is_featured', 'is_digital', 'categories')
    search_fields = ('title', 'slug', 'short_description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('price', 'is_published', 'is_featured', 'order')
    filter_horizontal = ('categories',)
    ordering = ('order', '-created_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'short_description', 'description')
        }),
        ('Цена и характеристики', {
            'fields': ('price', 'features', 'is_digital', 'stock_quantity')
        }),
        ('Медиа', {
            'fields': ('image',)
        }),
        ('Категории и теги', {
            'fields': ('categories',)
        }),
        ('Настройки публикации', {
            'fields': ('is_published', 'is_featured', 'order')
        }),
    )

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('title', 'product', 'percentage', 'start_date', 'end_date', 'max_activations', 'activations_used', 'is_active')
    list_filter = ('is_active', 'start_date', 'end_date', 'product')
    search_fields = ('title', 'product__title')
    date_hierarchy = 'start_date'
    list_editable = ('is_active',)
    ordering = ('-start_date',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'product', 'percentage')
        }),
        ('Период действия', {
            'fields': ('start_date', 'end_date')
        }),
        ('Ограничения', {
            'fields': ('max_activations', 'activations_used', 'is_active')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Редактирование существующего объекта
            return ('activations_used',)
        return ()

@admin.register(DiscountActivation)
class DiscountActivationAdmin(admin.ModelAdmin):
    list_display = ('user', 'discount', 'activated_at', 'order_id')
    list_filter = ('activated_at', 'discount')
    search_fields = ('user__username', 'discount__title', 'order_id')
    ordering = ('-activated_at',)
    readonly_fields = ('activated_at',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'payment_method', 'amount', 'status', 'created_at', 'anypay_invoice_id')
    list_filter = ('status', 'payment_method', 'created_at', 'product')
    search_fields = ('id', 'user__username', 'product__title', 'anypay_invoice_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

class ReportAdminLink:
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reports-dashboard/', self.admin_site.admin_view(
                __import__('core.views.reports.report_admin_view', fromlist=['report_dashboard']).report_dashboard
            ), name='report-dashboard'),
            path('reports-mail-dashboard/', self.admin_site.admin_view(
                __import__('core.views.reports.report_admin_view', fromlist=['report_mail_dashboard']).report_mail_dashboard
            ), name='report-mail-dashboard'),
        ]
        return custom_urls + urls

    def report_link(self, obj=None):
        url = reverse('admin:report-dashboard')
        return format_html('<a class="button" href="{}">Отчёты и графики</a>', url)
    report_link.short_description = 'Отчёты'
    report_link.allow_tags = True

    def mail_link(self, obj=None):
        url = reverse('admin:report-mail-dashboard')
        return format_html('<a class="button" href="{}">Почта (ящики)</a>', url)
    mail_link.short_description = 'Почта'
    mail_link.allow_tags = True


# Регистрируем custom_link для любой модели (например, UserProfile)
class UserProfileAdmin(ReportAdminLink, admin.ModelAdmin):
    list_display = ('user', 'group', 'avatar', 'report_link', 'mail_link')
    list_filter = ('group',)
    search_fields = ('user__username',)

@admin.register(GroupColor)
class GroupColorAdmin(admin.ModelAdmin):
    list_display = ('group', 'color')
    search_fields = ('group__name',)

# Переопределяем регистрацию UserProfile
try:
    admin.site.unregister(UserProfile)
except NotRegistered:
    pass
admin.site.register(UserProfile, UserProfileAdmin)

class EmailAccountAdmin(ReportAdminLink, admin.ModelAdmin):
    list_display = ('name', 'email', 'is_active', 'mail_link')
    search_fields = ('name', 'email')
    list_filter = ('is_active',)

admin.site.register(EmailAccount, EmailAccountAdmin)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'processor_type', 'is_active', 'sort_order')
    list_filter = ('processor_type', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'sort_order')
    ordering = ('sort_order', 'name')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('Настройки обработки', {
            'fields': ('processor_type', 'processor_config')
        }),
        ('Отображение', {
            'fields': ('is_active', 'sort_order')
        }),
    )


@admin.register(ShopSettings)
class ShopSettingsAdmin(admin.ModelAdmin):
    list_display = ('payments_enabled', 'updated_at')
    
    fieldsets = (
        ('Настройки оплаты', {
            'fields': ('payments_enabled', 'maintenance_message')
        }),
    )
    
    def has_add_permission(self, request):
        # Разрешаем создание только если записей нет
        return not ShopSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Запрещаем удаление
        return False
