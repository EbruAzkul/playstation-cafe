# tables/management/commands/test_email.py

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from tables.models import DailyReport, Session, Receipt, EmailRecipient

class Command(BaseCommand):
    help = 'Test email gönderme ve günlük rapor sistemi'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Test mail göndermek için email adresi'
        )
        parser.add_argument(
            '--daily-report',
            action='store_true',
            help='Bugün için günlük rapor oluştur ve gönder'
        )
        parser.add_argument(
            '--test-recipients',
            action='store_true',
            help='Test email alıcıları oluştur'
        )
        parser.add_argument(
            '--fake-data',
            action='store_true',
            help='Test için sahte veriler oluştur'
        )
    
    def handle(self, *args, **options):
        if options['test_recipients']:
            self.create_test_recipients()
        
        if options['fake_data']:
            self.create_fake_data()
        
        if options['email']:
            self.send_test_email(options['email'])
        
        if options['daily_report']:
            self.send_daily_report()
    
    def send_test_email(self, email):
        """Basit test email gönder"""
        try:
            send_mail(
                subject='🎮 PlayStation Kafe Test Maili',
                message='Bu bir test mailidir. Email sistemi çalışıyor! 🚀',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Test email başarıyla gönderildi: {email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Email gönderilirken hata: {e}')
            )
    
    def create_test_recipients(self):
        """Test email alıcıları oluştur"""
        from tables.models import EmailSetting
        
        # EmailSetting oluştur
        setting, created = EmailSetting.objects.get_or_create(
            name='Test Ayarları',
            defaults={'is_active': True}
        )
        
        # Test alıcıları
        test_recipients = [
            {
                'name': 'Test Kullanıcı 1',
                'email': 'test1@localhost.com',
                'recipient_type': 'daily_report'
            },
            {
                'name': 'Test Kullanıcı 2', 
                'email': 'test2@localhost.com',
                'recipient_type': 'daily_report'
            }
        ]
        
        for recipient_data in test_recipients:
            recipient, created = EmailRecipient.objects.get_or_create(
                email_setting=setting,
                email=recipient_data['email'],
                defaults=recipient_data
            )
            if created:
                self.stdout.write(f'✅ Test alıcı oluşturuldu: {recipient.email}')
            else:
                self.stdout.write(f'ℹ️ Test alıcı zaten var: {recipient.email}')
    
    def create_fake_data(self):
        """Test için sahte veriler oluştur"""
        from django.contrib.auth.models import User
        from tables.models import Table, Session, Receipt
        from decimal import Decimal
        
        # Test kullanıcısı
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={
                'email': 'test@localhost.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Test masası
        table, created = Table.objects.get_or_create(
            name='Test Masa 1',
            defaults={
                'playstation_ip': '192.168.1.100',
                'hourly_rate': Decimal('50.00'),
                'opening_fee': Decimal('10.00'),
                'status': 'available'
            }
        )
        
        # Bugün için test seansları oluştur
        today = timezone.now().date()
        
        for i in range(3):
            start_time = timezone.now().replace(hour=10+i*2, minute=0, second=0)
            end_time = start_time + timedelta(hours=1, minutes=30)
            
            session = Session.objects.create(
                table=table,
                user=user,
                start_time=start_time,
                end_time=end_time,
                opening_fee=table.opening_fee,
                hourly_rate=table.hourly_rate,
                gaming_amount=Decimal('85.00'),  # 1.5 saat * 50 + 10
                products_amount=Decimal('25.00'),
                total_amount=Decimal('110.00'),
                is_paid=True
            )
            
            # Fiş oluştur - benzersiz numara ile
            from datetime import datetime
            import random
            receipt_num = f'F{today.strftime("%Y%m%d")}{random.randint(100, 999)}'
            
            # Eğer fiş zaten varsa atla, yoksa oluştur
            if not Receipt.objects.filter(session=session).exists():
                try:
                    Receipt.objects.create(
                        session=session,
                        issued_by=user,
                        receipt_number=receipt_num
                    )
                except Exception as e:
                    # Eğer yine çakışma varsa farklı numara dene
                    receipt_num = f'F{today.strftime("%Y%m%d")}{random.randint(1000, 9999)}'
                    Receipt.objects.create(
                        session=session,
                        issued_by=user,
                        receipt_number=receipt_num
                    )
        
        self.stdout.write(self.style.SUCCESS('✅ Test verileri oluşturuldu'))
    
    def send_daily_report(self):
        """Günlük rapor gönder"""
        try:
            from tables.utils.email_utils import EmailService
            
            email_service = EmailService()
            result = email_service.send_daily_report()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Günlük rapor gönderildi: {result["recipients_count"]} alıcı')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Günlük rapor gönderilemedi: {result["error"]}')
                )
                
        except ImportError:
            self.stdout.write(
                self.style.ERROR('❌ EmailService bulunamadı. utils/email_utils.py dosyasını kontrol edin.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Günlük rapor hatası: {e}')
            )