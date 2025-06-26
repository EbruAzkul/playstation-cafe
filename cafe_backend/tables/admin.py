from django.contrib import admin
from django.utils.html import format_html
from .models import Table, Session, PlayStationDevice, Category, Product, SessionProduct, Receipt

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Ürün Sayısı'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'category__name']
    list_editable = ['price', 'is_active']
    ordering = ['category__name', 'name']

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'hourly_rate', 'opening_fee', 'playstation_ip', 'current_session_info', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'playstation_ip']
    list_editable = ['status', 'hourly_rate', 'opening_fee']
    ordering = ['name']
    
    def current_session_info(self, obj):
        session = obj.current_session
        if session:
            return format_html(
                '<span style="color: orange;">Aktif - {}dk</span>',
                session.duration_minutes
            )
        return format_html('<span style="color: green;">Müsait</span>')
    current_session_info.short_description = 'Seans Durumu'

class SessionProductInline(admin.TabularInline):
    model = SessionProduct
    extra = 0
    readonly_fields = ['total_price', 'added_at']
    fields = ['product', 'quantity', 'unit_price', 'total_price', 'added_at']

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['table', 'user', 'start_time', 'end_time', 'duration_display', 'total_amount', 'is_paid', 'is_reset']
    list_filter = ['start_time', 'end_time', 'table', 'is_paid', 'is_reset']
    search_fields = ['table__name', 'user__username']
    readonly_fields = ['duration_minutes', 'current_gaming_amount', 'current_total_amount']
    ordering = ['-start_time']
    inlines = [SessionProductInline]
    
    fieldsets = (
        ('Seans Bilgileri', {
            'fields': ('table', 'user', 'start_time', 'end_time', 'notes')
        }),
        ('Ücretlendirme', {
            'fields': ('opening_fee', 'hourly_rate', 'gaming_amount', 'products_amount', 'total_amount')
        }),
        ('Durum', {
            'fields': ('is_paid', 'is_reset')
        }),
        ('Hesaplamalar (Canlı)', {
            'fields': ('duration_minutes', 'current_gaming_amount', 'current_total_amount'),
            'classes': ('collapse',)
        })
    )
    
    def duration_display(self, obj):
        return f"{obj.duration_minutes} dk"
    duration_display.short_description = 'Süre'

@admin.register(SessionProduct)
class SessionProductAdmin(admin.ModelAdmin):
    list_display = ['session', 'product', 'quantity', 'unit_price', 'total_price', 'added_at']
    list_filter = ['added_at', 'product__category']
    search_fields = ['session__table__name', 'product__name']
    readonly_fields = ['total_price', 'added_at']
    ordering = ['-added_at']

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'session', 'total_amount', 'issued_by', 'issued_at']
    list_filter = ['issued_at', 'issued_by']
    search_fields = ['receipt_number', 'session__table__name']
    readonly_fields = ['receipt_number', 'issued_at']
    ordering = ['-issued_at']
    
    def total_amount(self, obj):
        return f"₺{obj.session.total_amount}"
    total_amount.short_description = 'Toplam Tutar'

@admin.register(PlayStationDevice)
class PlayStationDeviceAdmin(admin.ModelAdmin):
    list_display = ['table', 'device_type', 'mac_address', 'is_online', 'last_seen']
    list_filter = ['device_type', 'is_online']
    search_fields = ['table__name', 'mac_address']
    list_editable = ['is_online']