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
    
    name = models.CharField(max_length=50, verbose_name='Masa Adı')  # "Masa 1", "Masa 2"
    playstation_ip = models.GenericIPAddressField(verbose_name='PlayStation IP Adresi')  # "192.168.1.101"
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, default=50.00, verbose_name='Saatlik Ücret')  
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

class Session(models.Model):
    """Oyun seansı modeli"""
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='sessions', verbose_name='Masa')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Çalışan')  # Hangi çalışan açtı
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='Başlama Zamanı')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Bitiş Zamanı')
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Toplam Tutar')
    notes = models.TextField(blank=True, verbose_name='Notlar')
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
    def current_amount(self):
        """Mevcut tutarı hesapla"""
        minutes = self.duration_minutes
        hourly_rate = self.table.hourly_rate
        return (Decimal(minutes) / Decimal(60)) * hourly_rate
    
    def calculate_total(self):
        """Seansı bitirirken toplam tutarı hesapla"""
        if self.end_time:
            self.total_amount = self.current_amount
            self.save()
        return self.total_amount

class PlayStationDevice(models.Model):
    """PlayStation cihaz bilgileri"""
    DEVICE_TYPES = [
        ('PS4', 'PlayStation 4'),
        ('PS5', 'PlayStation 5'),
    ]
    
    table = models.OneToOneField(Table, on_delete=models.CASCADE, related_name='playstation', verbose_name='Masa')
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES, verbose_name='Cihaz Tipi')
    mac_address = models.CharField(max_length=17, verbose_name='MAC Adresi')  # PlayStation'un MAC adresi
    is_online = models.BooleanField(default=False, verbose_name='Online')
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name='Son Görülme')
    
    class Meta:
        verbose_name = 'PlayStation'
        verbose_name_plural = 'PlayStation Cihazları'
    
    def __str__(self):
        return f"{self.table.name} - {self.device_type}"