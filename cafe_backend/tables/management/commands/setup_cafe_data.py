from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tables.models import Table, Category, Product, PlayStationDevice


class Command(BaseCommand):
    help = 'PlayStation Cafe için temel verileri oluştur'

    def handle(self, *args, **options):
        self.stdout.write('PlayStation Cafe veritabanı hazırlanıyor...')
        
        # Admin kullanıcı oluştur (yoksa)
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@cafe.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Admin kullanıcı oluşturuldu (admin/admin123)'))

        # Kategoriler oluştur
        categories_data = [
            'İçecekler',
            'Atıştırmalıklar', 
            'Ana Yemek'
        ]
        
        categories = {}
        for cat_name in categories_data:
            category, created = Category.objects.get_or_create(name=cat_name)
            categories[cat_name] = category
            if created:
                self.stdout.write(f'Kategori oluşturuldu: {cat_name}')

        # Ürünler oluştur
        products_data = [
            # İçecekler
            ('Kola', 'İçecekler', 8.00),
            ('Su', 'İçecekler', 3.00),
            ('Çay', 'İçecekler', 5.00),
            ('Kahve', 'İçecekler', 12.00),
            ('Ayran', 'İçecekler', 4.00),
            ('Meyve Suyu', 'İçecekler', 6.00),
            
            # Atıştırmalıklar
            ('Çips', 'Atıştırmalıklar', 10.00),
            ('Kek', 'Atıştırmalıklar', 15.00),
            ('Sandviç', 'Atıştırmalıklar', 25.00),
            ('Bisküvi', 'Atıştırmalıklar', 7.00),
            ('Kuruyemiş', 'Atıştırmalıklar', 12.00),
            
            # Ana Yemek
            ('Hamburger', 'Ana Yemek', 35.00),
            ('Pizza Dilim', 'Ana Yemek', 20.00),
            ('Tost', 'Ana Yemek', 18.00),
            ('Döner', 'Ana Yemek', 30.00)
        ]
        
        for name, cat_name, price in products_data:
            product, created = Product.objects.get_or_create(
                name=name,
                category=categories[cat_name],
                defaults={'price': price}
            )
            if created:
                self.stdout.write(f'Ürün oluşturuldu: {name} - ₺{price}')

        # Masalar oluştur (4 masa)
        tables_data = [
            ('Masa 1', '192.168.1.101', 50.00, 10.00, 'PS5'),
            ('Masa 2', '192.168.1.102', 50.00, 10.00, 'PS4'),
            ('Masa 3', '192.168.1.103', 45.00, 10.00, 'PS5'),
            ('Masa 4', '192.168.1.104', 45.00, 10.00, 'PS4'),
        ]
        
        for name, ip, hourly, opening, device_type in tables_data:
            table, created = Table.objects.get_or_create(
                name=name,
                defaults={
                    'playstation_ip': ip,
                    'hourly_rate': hourly,
                    'opening_fee': opening,
                    'status': 'available'
                }
            )
            if created:
                self.stdout.write(f'Masa oluşturuldu: {name}')
                
                # PlayStation cihaz bilgisi ekle
                playstation, ps_created = PlayStationDevice.objects.get_or_create(
                    table=table,
                    defaults={
                        'device_type': device_type,
                        'mac_address': f'00:11:22:33:44:{50 + table.id:02d}',
                        'is_online': False
                    }
                )
                if ps_created:
                    self.stdout.write(f'PlayStation cihazı eklendi: {device_type}')

        # Mevcut toplam sayıları göster
        table_count = Table.objects.count()
        category_count = Category.objects.count() 
        product_count = Product.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'''
=== PlayStation Cafe Kurulumu Tamamlandı ===
Masalar: {table_count}
Kategoriler: {category_count}
Ürünler: {product_count}

Admin Panel: http://127.0.0.1:8000/admin/
Kullanıcı: admin
Şifre: admin123

API Test: http://127.0.0.1:8000/api/tables/
'''))