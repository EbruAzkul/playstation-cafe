from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Table, Session, PlayStationDevice, Category, Product, SessionProduct, Receipt, StockMovement

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'total_stock_value', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Ürün Sayısı'
    
    def total_stock_value(self, obj):
        """Kategorideki toplam stok değeri"""
        total = obj.products.aggregate(
            total=Sum(models.F('current_stock') * models.F('price'))
        )['total'] or 0
        return f"₺{total:.2f}"
    total_stock_value.short_description = 'Toplam Stok Değeri'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'current_stock', 'stock_status_colored', 'min_stock_level', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'category__name']
    list_editable = ['price', 'current_stock', 'min_stock_level', 'is_active']
    ordering = ['category__name', 'name']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'category', 'price', 'is_active')
        }),
        ('Stok Yönetimi', {
            'fields': ('current_stock', 'min_stock_level', 'max_stock_level', 'stock_unit'),
            'classes': ('wide',)
        }),
    )
    
    def stock_status_colored(self, obj):
        """Renkli stok durumu"""
        if obj.is_out_of_stock:
            color = 'red'
            icon = '❌'
        elif obj.is_low_stock:
            color = 'orange'
            icon = '⚠️'
        else:
            color = 'green'
            icon = '✅'
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.stock_status_display
        )
    stock_status_colored.short_description = 'Stok Durumu'
    
    actions = ['add_stock', 'remove_stock']
    
    def add_stock(self, request, queryset):
        """Toplu stok ekleme"""
        # Bu action için custom view yazılabilir
        self.message_user(request, f"{queryset.count()} ürün için stok ekleme işlemi başlatıldı.")
    add_stock.short_description = "Seçili ürünlere stok ekle"
    
    def remove_stock(self, request, queryset):
        """Toplu stok çıkarma"""
        self.message_user(request, f"{queryset.count()} ürün için stok çıkarma işlemi başlatıldı.")
    remove_stock.short_description = "Seçili ürünlerden stok çıkar"

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity_formatted', 'old_stock', 'new_stock', 'total_cost', 'supplier', 'created_by', 'created_at']
    list_filter = ['movement_type', 'created_at', 'product__category']
    search_fields = ['product__name', 'supplier', 'notes']
    # Bu alanları readonly'den çıkardık ki elle girebilesin:
    readonly_fields = ['total_cost', 'session_product', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Hareket Bilgileri', {
            'fields': ('product', 'movement_type', 'quantity', 'old_stock', 'new_stock')
        }),
        ('Maliyet Bilgileri', {
            'fields': ('unit_cost', 'total_cost', 'supplier'),
            'classes': ('collapse',)
        }),
        ('Ekstra Bilgiler', {
            'fields': ('notes', 'session_product', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def quantity_formatted(self, obj):
        """Miktarı işaretle birlikte göster"""
        if obj.quantity > 0:
            return format_html('<span style="color: green;">+{}</span>', obj.quantity)
        else:
            return format_html('<span style="color: red;">{}</span>', obj.quantity)
    quantity_formatted.short_description = 'Miktar'
    
    def save_model(self, request, obj, form, change):
        """Stok hareketi kaydedilirken ürün stokunu güncelle"""
        if not change:  # Yeni kayıt
            obj.created_by = request.user
            super().save_model(request, obj, form, change)
            
            # Ürün stokunu güncelle
            product = obj.product
            product.current_stock = obj.new_stock
            product.save()
        else:
            super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        """Manuel stok hareketi ekleme izni"""
        return request.user.is_superuser or request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        """Stok hareketi değiştirme izni yok (güvenlik için)"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Stok hareketi silme izni yok (sadece superuser)"""
        return request.user.is_superuser

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
    list_display = ['session', 'product', 'quantity', 'unit_price', 'total_price', 'stock_effect', 'added_at']
    list_filter = ['added_at', 'product__category']
    search_fields = ['session__table__name', 'product__name']
    readonly_fields = ['total_price', 'added_at']
    ordering = ['-added_at']
    
    def stock_effect(self, obj):
        """Stok etkisi"""
        return format_html(
            '<span style="color: red;">-{} {}</span>',
            obj.quantity, obj.product.stock_unit
        )
    stock_effect.short_description = 'Stok Etkisi'

# Custom tarih filtreleri
class CustomDateFilter(admin.SimpleListFilter):
    """Özel tarih filtreleri"""
    title = 'Kesilme Zamanı'
    parameter_name = 'custom_date'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Bugün'),
            ('yesterday', 'Dün'), 
            ('last_7_days', 'Son 7 Gün'),
            ('last_30_days', 'Son 30 Gün'),
            ('this_week', 'Bu Hafta'),
            ('this_month', 'Bu Ay'),
            ('last_month', 'Geçen Ay'),
            ('custom_range', 'Tarih Aralığı Gir'),
        )

    def queryset(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today = now.date()
        
        if self.value() == 'today':
            return queryset.filter(issued_at__date=today)
        
        elif self.value() == 'yesterday':
            yesterday = today - timedelta(days=1)
            return queryset.filter(issued_at__date=yesterday)
        
        elif self.value() == 'last_7_days':
            start_date = today - timedelta(days=7)
            return queryset.filter(issued_at__date__gte=start_date)
        
        elif self.value() == 'last_30_days':
            start_date = today - timedelta(days=30)
            return queryset.filter(issued_at__date__gte=start_date)
        
        elif self.value() == 'this_week':
            start_week = today - timedelta(days=today.weekday())
            return queryset.filter(issued_at__date__gte=start_week)
        
        elif self.value() == 'this_month':
            start_month = today.replace(day=1)
            return queryset.filter(issued_at__date__gte=start_month)
        
        elif self.value() == 'last_month':
            # Geçen ayın ilk günü
            if today.month == 1:
                last_month_start = today.replace(year=today.year-1, month=12, day=1)
                last_month_end = today.replace(day=1) - timedelta(days=1)
            else:
                last_month_start = today.replace(month=today.month-1, day=1)
                last_month_end = today.replace(day=1) - timedelta(days=1)
            
            return queryset.filter(
                issued_at__date__gte=last_month_start,
                issued_at__date__lte=last_month_end
            )
        
        # Manuel tarih aralığı için
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date and end_date:
            try:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                return queryset.filter(
                    issued_at__date__gte=start,
                    issued_at__date__lte=end
                )
            except ValueError:
                pass
        
        return queryset

class ManualDateRangeFilter(admin.SimpleListFilter):
    """Manuel tarih aralığı filtresi"""
    title = 'Manuel Tarih Seçimi'
    parameter_name = 'date_range'
    template = 'admin/date_range_filter.html'

    def lookups(self, request, model_admin):
        return (
            ('custom', 'Tarih Aralığı Belirle'),
        )

    def choices(self, changelist):
        # Filtrenin HTML'ini özelleştir
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'display': title,
            }

    def queryset(self, request, queryset):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date and end_date:
            try:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                return queryset.filter(
                    issued_at__date__gte=start,
                    issued_at__date__lte=end
                )
            except ValueError:
                pass
        return queryset

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'session_info', 'total_amount', 'issued_by', 'issued_at']
    list_filter = [
        CustomDateFilter,  # Özel tarih filtresi
        'issued_by',  # Kesen kişi filtresi
        'session__table',  # Masa filtresi
    ]
    search_fields = ['receipt_number', 'session__table__name']
    readonly_fields = ['receipt_number', 'issued_at']
    ordering = ['-issued_at']
    date_hierarchy = 'issued_at'  # Üstte tarih navigasyonu
    
    # Manuel tarih aralığı için custom view
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Tarih aralığı formu için context
        extra_context['date_range_form'] = True
        extra_context['start_date'] = request.GET.get('start_date', '')
        extra_context['end_date'] = request.GET.get('end_date', '')
        
        return super().changelist_view(request, extra_context)
    
    class Media:
        css = {
            'all': ('admin/css/date_range_filter.css',)
        }
        js = ('admin/js/date_range_filter.js',)
    
    fieldsets = (
        ('Fiş Bilgileri', {
            'fields': ('receipt_number', 'session', 'issued_at')
        }),
        ('Kesen Kişi', {
            'fields': ('issued_by',)
        }),
    )
    
    def session_info(self, obj):
        """Seans bilgilerini göster"""
        session = obj.session
        duration = f"{session.duration_minutes}dk" if session.duration_minutes else "0dk"
        return format_html(
            '<strong>{}</strong><br/>🕐 {} | 🎮 {} | 🛒 {}',
            session.table.name,
            duration,
            f"₺{session.gaming_amount}",
            f"₺{session.products_amount}"
        )
    session_info.short_description = 'Seans Detayı'
    
    def total_amount(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: #16a34a;">₺{}</span>',
            f"{obj.session.total_amount:.2f}"
        )
    total_amount.short_description = 'Toplam Tutar'
    
    # Custom actions
    actions = ['export_selected_report']
    
    def export_selected_report(self, request, queryset):
        """Seçili fişler için rapor"""
        total = sum(r.session.total_amount for r in queryset)
        count = queryset.count()
        
        # Tarih aralığı bilgisi
        dates = queryset.aggregate(
            min_date=models.Min('issued_at'),
            max_date=models.Max('issued_at')
        )
        
        date_info = ""
        if dates['min_date'] and dates['max_date']:
            if dates['min_date'].date() == dates['max_date'].date():
                date_info = f" ({dates['min_date'].strftime('%d.%m.%Y')})"
            else:
                date_info = f" ({dates['min_date'].strftime('%d.%m.%Y')} - {dates['max_date'].strftime('%d.%m.%Y')})"
        
        self.message_user(
            request,
            f"📊 Rapor{date_info}: {count} fiş, Toplam: ₺{total:.2f}"
        )
    export_selected_report.short_description = "📊 Seçili fişler için rapor oluştur"

@admin.register(PlayStationDevice)
class PlayStationDeviceAdmin(admin.ModelAdmin):
    list_display = ['table', 'device_type', 'mac_address', 'is_online', 'last_seen']
    list_filter = ['device_type', 'is_online']
    search_fields = ['table__name', 'mac_address']
    list_editable = ['is_online']

# Admin Dashboard için özel görünümler
class StockLevelFilter(admin.SimpleListFilter):
    """Stok seviyesine göre filtreleme"""
    title = 'Stok Seviyesi'
    parameter_name = 'stock_level'

    def lookups(self, request, model_admin):
        return (
            ('out', 'Stok Tükendi'),
            ('low', 'Stok Azalıyor'),
            ('normal', 'Stok Normal'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'out':
            return queryset.filter(current_stock=0)
        if self.value() == 'low':
            return queryset.filter(current_stock__gt=0, current_stock__lte=models.F('min_stock_level'))
        if self.value() == 'normal':
            return queryset.filter(current_stock__gt=models.F('min_stock_level'))

# ProductAdmin'e stok filtresi ekle
ProductAdmin.list_filter = ['category', 'is_active', StockLevelFilter, 'created_at']

# Custom admin actions
@admin.action(description='Stok raporu oluştur')
def generate_stock_report(modeladmin, request, queryset):
    """Seçili ürünler için stok raporu oluştur"""
    # Bu daha sonra PDF/Excel raporu olarak geliştirilebilir
    total_value = 0
    low_stock_count = 0
    
    for product in queryset:
        total_value += product.current_stock * product.price
        if product.is_low_stock:
            low_stock_count += 1
    
    modeladmin.message_user(
        request, 
        f"Rapor: {queryset.count()} ürün, Toplam değer: ₺{total_value:.2f}, Düşük stok: {low_stock_count} ürün"
    )

# ProductAdmin'e action ekle
ProductAdmin.actions.append(generate_stock_report)