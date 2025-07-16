from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.db import transaction
from django.utils.html import format_html
from django.db.models import Sum, F
import pandas as pd
import io

from .models import (
    Table, Session, PlayStationDevice, Category, Product, 
    SessionProduct, Receipt, StockMovement, 
    EmailSetting, EmailRecipient, EmailLog, DailyReport
)
from .forms import ExcelUploadForm

try:
    from cafe_backend.tables.utils.email_utils import EmailService
except ImportError:
    EmailService = None


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'total_stock_value', 'created_at']
    search_fields = ['name']
    ordering = ['name']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Ürün Sayısı'

    def total_stock_value(self, obj):
        total = obj.products.aggregate(
            total=Sum(F('current_stock') * F('price'))
        )['total'] or 0
        return f"₺{total:.2f}"
    total_stock_value.short_description = 'Toplam Stok Değeri'
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'price', 'current_stock',
        'stock_status_colored', 'min_stock_level', 'is_active', 'created_at'
    ]
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('excel-import/', self.admin_site.admin_view(self.excel_import_view), name='product_excel_import'),
            path('excel-template/', self.admin_site.admin_view(self.excel_template_view), name='product_excel_template'),
        ]
        return custom_urls + urls

    def excel_import_view(self, request):
        if request.method == 'POST':
            form = ExcelUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    result = self.process_excel_file(
                        excel_file=request.FILES['excel_file'],
                        user=request.user,
                        update_existing=form.cleaned_data['update_existing'],
                        create_categories=form.cleaned_data['create_categories']
                    )
                    if result['success']:
                        messages.success(request, format_html(
                            '✅ <strong>Excel import başarılı!</strong><br>'
                            '📦 {} yeni ürün<br>'
                            '🔄 {} ürün güncellendi<br>'
                            '📊 {} stok hareketi',
                            result['created_products'],
                            result['updated_products'],
                            result['stock_movements']
                        ))
                        if result['errors']:
                            messages.warning(request, format_html(
                                '⚠️ {} hata oluştu:<br>{}',
                                len(result['errors']),
                                '<br>'.join(result['errors'][:5]) +
                                (f'<br>... ve {len(result["errors"]) - 5} hata daha' if len(result['errors']) > 5 else '')
                            ))
                    else:
                        messages.error(request, f"❌ Hata: {result['error']}")
                except Exception as e:
                    messages.error(request, f"❌ İşleme hatası: {str(e)}")
                return redirect('admin:product_excel_import')
        else:
            form = ExcelUploadForm()

        context = {
            'form': form,
            'title': 'Excel ile Ürün Import',
            'opts': self.model._meta,
            'has_view_permission': True,
            'stats': {
                'total_products': Product.objects.count(),
                'total_categories': Category.objects.count(),
                'active_products': Product.objects.filter(is_active=True).count(),
                'low_stock_products': Product.objects.filter(
                    is_active=True,
                    current_stock__lte=F('min_stock_level')
                ).count()
            }
        }
        return render(request, 'admin/excel_import.html', context)

    def excel_template_view(self, request):
        template_data = {
            'ürün_adı': ['Cola', 'Cips', 'Su', 'Çikolata', 'Red Bull'],
            'kategori': ['İçecek', 'Atıştırmalık', 'İçecek', 'Tatlı', 'Enerji'],
            'fiyat': [8.5, 12, 3, 7.5, 15],
            'stok_miktarı': [50, 30, 100, 40, 25],
            'min_stok': [10, 5, 20, 8, 5],
            'max_stok': [200, 100, 500, 150, 80],
            'birim': ['adet', 'adet', 'adet', 'adet', 'adet'],
            'tedarikçi': ['Coca Cola', 'Frito-Lay', 'Nestle', 'Mars', 'Red Bull'],
            'birim_maliyet': [6.00, 8.5, 2.0, 5.5, 11.0]
        }
        df = pd.DataFrame(template_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ürünler')
            worksheet = writer.sheets['Ürünler']
            from openpyxl.styles import Font
            for cell in worksheet[1]:
                cell.font = Font(bold=True)
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="urun_template.xlsx"'
        return response
    def process_excel_file(self, excel_file, user, update_existing=True, create_categories=True):
        try:
            df = pd.read_excel(excel_file, sheet_name=0)

            required_columns = ['ürün_adı', 'kategori', 'fiyat', 'stok_miktarı']
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return {'success': False, 'error': f"Eksik sütunlar: {', '.join(missing)}"}

            created_products = 0
            updated_products = 0
            stock_movements = 0
            errors = []

            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        product_name = str(row['ürün_adı']).strip()
                        category_name = str(row['kategori']).strip()
                        if not product_name or product_name == 'nan':
                            errors.append(f"{index+2}. satır: Ürün adı boş")
                            continue
                        if not category_name or category_name == 'nan':
                            errors.append(f"{index+2}. satır: Kategori boş")
                            continue

                        price = float(row['fiyat'])
                        stock_quantity = int(row['stok_miktarı'])
                        min_stock = int(row.get('min_stok', 5)) if pd.notna(row.get('min_stok')) else 5
                        max_stock = int(row.get('max_stok', 100)) if pd.notna(row.get('max_stok')) else 100
                        stock_unit = str(row.get('birim', 'adet')).strip()
                        supplier = str(row.get('tedarikçi', '')).strip()
                        unit_cost = float(row.get('birim_maliyet', price * 0.7))

                        if create_categories:
                            category, _ = Category.objects.get_or_create(name=category_name)
                        else:
                            try:
                                category = Category.objects.get(name=category_name)
                            except Category.DoesNotExist:
                                errors.append(f"{index+2}. satır: Kategori bulunamadı")
                                continue

                        product, created = Product.objects.get_or_create(
                            name=product_name,
                            defaults={
                                'category': category,
                                'price': price,
                                'current_stock': 0,
                                'min_stock_level': min_stock,
                                'max_stock_level': max_stock,
                                'stock_unit': stock_unit,
                                'is_active': True
                            }
                        )

                        if created:
                            created_products += 1
                        elif update_existing:
                            product.category = category
                            product.price = price
                            product.min_stock_level = min_stock
                            product.max_stock_level = max_stock
                            product.stock_unit = stock_unit
                            product.save()
                            updated_products += 1

                        if stock_quantity > 0:
                            old_stock = product.current_stock
                            new_stock = old_stock + stock_quantity

                            StockMovement.objects.create(
                                product=product,
                                movement_type='in',
                                quantity=stock_quantity,
                                old_stock=old_stock,
                                new_stock=new_stock,
                                unit_cost=unit_cost,
                                total_cost=unit_cost * stock_quantity,
                                supplier=supplier,
                                notes=f'Excel import - {excel_file.name}',
                                created_by=user
                            )

                            product.current_stock = new_stock
                            product.save()
                            stock_movements += 1

                    except Exception as e:
                        errors.append(f"{index+2}. satır: {str(e)}")

            return {
                'success': True,
                'created_products': created_products,
                'updated_products': updated_products,
                'stock_movements': stock_movements,
                'errors': errors
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}
@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'movement_type', 'quantity_formatted',
        'old_stock', 'new_stock', 'total_cost', 'supplier',
        'created_by', 'created_at'
    ]
    list_filter = ['movement_type', 'created_at', 'product__category']
    search_fields = ['product__name', 'supplier', 'notes']
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
        if obj.quantity > 0:
            return format_html('<span style="color: green;">+{}</span>', obj.quantity)
        return format_html('<span style="color: red;">{}</span>', obj.quantity)
    quantity_formatted.short_description = 'Miktar'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            super().save_model(request, obj, form, change)
            product = obj.product
            product.current_stock = obj.new_stock
            product.save()
        else:
            super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
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
                '<span style="color: orange;">Aktif - {} dk</span>',
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
        }),
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
        return format_html(
            '<span style="color: red;">-{} {}</span>',
            obj.quantity, obj.product.stock_unit
        )
    stock_effect.short_description = 'Stok Etkisi'
@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'session_info', 'total_amount', 'issued_by', 'issued_at']
    list_filter = ['issued_by', 'session__table']
    search_fields = ['receipt_number', 'session__table__name']
    readonly_fields = ['receipt_number', 'issued_at']
    ordering = ['-issued_at']

    fieldsets = (
        ('Fiş Bilgileri', {
            'fields': ('receipt_number', 'session', 'issued_at')
        }),
        ('Kesen Kişi', {
            'fields': ('issued_by',)
        }),
    )

    def session_info(self, obj):
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
@admin.register(PlayStationDevice)
class PlayStationDeviceAdmin(admin.ModelAdmin):
    list_display = ['table', 'device_type', 'mac_address', 'is_online', 'last_seen']
    list_filter = ['device_type', 'is_online']
    search_fields = ['table__name', 'mac_address']
    list_editable = ['is_online']
@admin.register(EmailSetting)
class EmailSettingAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'recipient_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']

    def recipient_count(self, obj):
        return obj.recipients.filter(is_active=True).count()
    recipient_count.short_description = 'Aktif Alıcı Sayısı'


@admin.register(EmailRecipient)
class EmailRecipientAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'recipient_type', 'is_active', 'created_at']
    list_filter = ['recipient_type', 'is_active', 'created_at']
    search_fields = ['name', 'email']
    list_editable = ['is_active']
    ordering = ['recipient_type', 'name']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['email_type', 'status', 'sent_at', 'created_at']
    list_filter = ['email_type', 'status', 'sent_at']
    readonly_fields = ['email_type', 'recipients', 'subject', 'sent_at', 'created_at']
    ordering = ['-created_at']


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ['report_date', 'total_receipts', 'total_revenue', 'email_sent']
    list_filter = ['report_date', 'email_sent']
    ordering = ['-report_date']
