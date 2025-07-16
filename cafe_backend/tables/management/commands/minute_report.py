# tables/management/commands/minute_report.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from tables.models import Session, Receipt, DailyReport
from decimal import Decimal

class Command(BaseCommand):
    help = 'Dakika bazında test raporu gönder (test amaçlı)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=5,
            help='Kaç dakika öncesinden itibaren rapor oluştur (varsayılan: 5)'
        )
    
    def handle(self, *args, **options):
        minutes_ago = options['minutes']
        start_time = timezone.now() - timedelta(minutes=minutes_ago)
        
        self.stdout.write(
            f'📊 Son {minutes_ago} dakikanın raporu oluşturuluyor...'
        )
        
        # Son X dakikadaki seansları bul
        recent_sessions = Session.objects.filter(
            start_time__gte=start_time
        )
        
        # Son X dakikadaki fişleri bul
        recent_receipts = Receipt.objects.filter(
            issued_at__gte=start_time
        )
        
        # İstatistikleri hesapla
        total_sessions = recent_sessions.count()
        total_receipts = recent_receipts.count()
        total_revenue = sum(r.session.total_amount for r in recent_receipts)
        gaming_revenue = sum(r.session.gaming_amount for r in recent_receipts)
        products_revenue = sum(r.session.products_amount for r in recent_receipts)
        
        # Ortalama seans süresi
        completed_sessions = recent_sessions.filter(end_time__isnull=False)
        if completed_sessions.exists():
            avg_duration = sum(s.duration_minutes for s in completed_sessions) / completed_sessions.count()
        else:
            avg_duration = 0
        
        # Raporu yazdır
        self.stdout.write('=' * 50)
        self.stdout.write(f'⏰ RAPOR ZAMANLAĞI: Son {minutes_ago} dakika')
        self.stdout.write(f'📅 TARİH: {timezone.now().strftime("%d.%m.%Y %H:%M")}')
        self.stdout.write('=' * 50)
        self.stdout.write(f'🎮 Toplam Seans: {total_sessions}')
        self.stdout.write(f'📄 Toplam Fiş: {total_receipts}')
        self.stdout.write(f'💰 Toplam Gelir: ₺{total_revenue:.2f}')
        self.stdout.write(f'🎲 Oyun Geliri: ₺{gaming_revenue:.2f}')
        self.stdout.write(f'🛒 Ürün Geliri: ₺{products_revenue:.2f}')
        self.stdout.write(f'⏱️ Ortalama Seans: {avg_duration:.1f} dakika')
        self.stdout.write('=' * 50)
        
        # Email gönder
        if total_receipts > 0:
            self.send_minute_report_email(
                minutes_ago, total_sessions, total_receipts, 
                total_revenue, gaming_revenue, products_revenue, avg_duration
            )
        else:
            self.stdout.write('ℹ️ Fiş bulunamadığı için email gönderilmedi.')
    
    def send_minute_report_email(self, minutes, sessions, receipts, total, gaming, products, avg_duration):
        """Dakikalık raporu email ile gönder"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f'🎮 PlayStation Kafe - Son {minutes} Dakika Raporu'
        
        message = f'''
🎮 PlayStation Kafe Dakikalık Rapor
{'=' * 40}

⏰ Rapor Periyodu: Son {minutes} dakika
📅 Tarih: {timezone.now().strftime("%d.%m.%Y %H:%M")}

📊 ÖZET İSTATİSTİKLER:
{'=' * 40}
🎮 Toplam Seans: {sessions}
📄 Toplam Fiş: {receipts}
💰 Toplam Gelir: ₺{total:.2f}
🎲 Oyun Geliri: ₺{gaming:.2f}
🛒 Ürün Geliri: ₺{products:.2f}
⏱️ Ortalama Seans Süresi: {avg_duration:.1f} dakika

Bu bir test mesajıdır.
Gerçek günlük raporlar günde bir kez gönderilir.

PlayStation Kafe Yönetim Sistemi
        '''
        
        # Test email adreslerine gönder
        test_emails = ['test@localhost.com', 'admin@localhost.com']
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=test_emails,
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Dakikalık rapor email olarak gönderildi!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Email gönderilirken hata: {e}')
            )