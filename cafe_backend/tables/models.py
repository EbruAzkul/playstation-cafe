from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Table(models.Model):
    """PlayStation masası modeli"""
    STATUS_CHOICES = [
        ('available', 'Müsait'),
        ('occupied', 'Dolu'),
        ('maintenance', 'Bakımda'),
    ]
    
    name = models.CharField(max_length=50, verbose_name='Masa Adı')
    playstation_ip = models.GenericIPAddressField(verbose_name='PlayStation IP Adresi')
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, default=50.00, verbose_name='Saatlik Ücret')
    opening_fee = models.DecimalField(max_digits=6, decimal_places=2, default=10.00, verbose_name='Masa Açma Ücreti')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', verbose_name='Durum')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Masa'
        verbose_name_plural = 'Masalar'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    @property
    def is_available(self):
        return self.status == 'available'
    
    @property
    def current_session(self):
        """Aktif seansı döndür"""
        return self.sessions.filter(end_time__isnull=True).first()

class Category(models.Model):
    """Ürün kategorileri (İçecek, Yiyecek, Atıştırmalık vb.)"""
    name = models.CharField(max_length=100, verbose_name='Kategori Adı')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategoriler'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Satılabilir ürünler (Kola, Çips, Su vb.)"""
    name = models.CharField(max_length=100, verbose_name='Ürün Adı')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Kategori')
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Fiyat')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ürün'
        verbose_name_plural = 'Ürünler'
        ordering = ['category__name', 'name']
    
    def __str__(self):
        return f"{self.name} - ₺{self.price}"

class Session(models.Model):
    """Oyun seansı modeli"""
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='sessions', verbose_name='Masa')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Çalışan')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='Başlama Zamanı')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Bitiş Zamanı')
    
    # Ücretlendirme alanları
    opening_fee = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Masa Açma Ücreti')
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Saatlik Ücret')
    gaming_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Oyun Tutarı')
    products_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Ürün Tutarı')
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Toplam Tutar')
    
    # Diğer alanlar
    notes = models.TextField(blank=True, verbose_name='Notlar')
    is_paid = models.BooleanField(default=False, verbose_name='Ödendi')
    is_reset = models.BooleanField(default=False, verbose_name='Reset Edildi')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Seans'
        verbose_name_plural = 'Seanslar'
        ordering = ['-start_time']
    
    def __str__(self):
        status = "Devam ediyor" if not self.end_time else "Tamamlandı"
        return f"{self.table.name} - {self.start_time.strftime('%d.%m.%Y %H:%M')} - {status}"
    
    @property
    def duration_minutes(self):
        """Seans süresini dakika olarak döndür"""
        end = self.end_time or timezone.now()
        duration = end - self.start_time
        return int(duration.total_seconds() / 60)
    
    @property
    def current_gaming_amount(self):
        """Mevcut oyun tutarını hesapla (masa açma + saatlik)"""
        minutes = self.duration_minutes
        hourly_amount = (Decimal(minutes) / Decimal(60)) * self.hourly_rate
        return self.opening_fee + hourly_amount
    
    @property
    def current_total_amount(self):
        """Mevcut toplam tutarı hesapla"""
        return self.current_gaming_amount + self.products_amount
    
    def save(self, *args, **kwargs):
        # İlk kayıt sırasında masa ücretlerini al
        if not self.pk:
            self.opening_fee = self.table.opening_fee
            self.hourly_rate = self.table.hourly_rate
        super().save(*args, **kwargs)
    
    def calculate_final_amounts(self):
        """Seansı bitirirken final tutarları hesapla"""
        if self.end_time:
            self.gaming_amount = self.current_gaming_amount
            self.total_amount = self.current_total_amount
            self.save()

class SessionProduct(models.Model):
    """Seans sırasında satılan ürünler"""
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='products', verbose_name='Seans')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Ürün')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Adet')
    unit_price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Birim Fiyat')
    total_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Toplam Fiyat')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Eklenme Zamanı')
    
    class Meta:
        verbose_name = 'Seans Ürünü'
        verbose_name_plural = 'Seans Ürünleri'
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.session} - {self.product.name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        # İlk kayıt sırasında fiyatları al
        if not self.pk:
            self.unit_price = self.product.price
        
        # Toplam fiyatı hesapla
        self.total_price = self.unit_price * self.quantity
        
        super().save(*args, **kwargs)
        
        # Session'ın ürün tutarını güncelle
        self.update_session_products_amount()
    
    def delete(self, *args, **kwargs):
        session = self.session
        super().delete(*args, **kwargs)
        self.update_session_products_amount_for_session(session)
    
    def update_session_products_amount(self):
        """Bu seanstaki tüm ürünlerin toplam tutarını güncelle"""
        self.update_session_products_amount_for_session(self.session)
    
    @staticmethod
    def update_session_products_amount_for_session(session):
        """Belirtilen seans için ürün tutarını güncelle"""
        total = session.products.aggregate(
            total=models.Sum('total_price')
        )['total'] or Decimal('0')
        
        session.products_amount = total
        session.save()

class Receipt(models.Model):
    """Fiş/Fatura modeli"""
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='receipt', verbose_name='Seans')
    receipt_number = models.CharField(max_length=20, unique=True, verbose_name='Fiş Numarası')
    issued_at = models.DateTimeField(auto_now_add=True, verbose_name='Kesilme Zamanı')
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Kesen Çalışan')
    
    class Meta:
        verbose_name = 'Fiş'
        verbose_name_plural = 'Fişler'
        ordering = ['-issued_at']
    
    def __str__(self):
        return f"Fiş #{self.receipt_number} - {self.session.table.name}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Fiş numarası oluştur (örnek: F20241224001)
            from datetime import datetime
            today = datetime.now().strftime('%Y%m%d')
            last_receipt = Receipt.objects.filter(
                receipt_number__startswith=f'F{today}'
            ).order_by('-receipt_number').first()
            
            if last_receipt:
                last_num = int(last_receipt.receipt_number[-3:])
                new_num = f"{last_num + 1:03d}"
            else:
                new_num = "001"
            
            self.receipt_number = f"F{today}{new_num}"
        
        super().save(*args, **kwargs)

class PlayStationDevice(models.Model):
    """PlayStation cihaz bilgileri"""
    DEVICE_TYPES = [
        ('PS4', 'PlayStation 4'),
        ('PS5', 'PlayStation 5'),
    ]
    
    table = models.OneToOneField(Table, on_delete=models.CASCADE, related_name='playstation', verbose_name='Masa')
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES, verbose_name='Cihaz Tipi')
    mac_address = models.CharField(max_length=17, verbose_name='MAC Adresi')
    is_online = models.BooleanField(default=False, verbose_name='Online')
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name='Son Görülme')
    
    class Meta:
        verbose_name = 'PlayStation'
        verbose_name_plural = 'PlayStation Cihazları'
    
    def __str__(self):
        return f"{self.table.name} - {self.device_type}"