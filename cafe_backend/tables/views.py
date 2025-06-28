from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, F, Q
from decimal import Decimal
from .models import Table, Session, PlayStationDevice, Category, Product, SessionProduct, Receipt, StockMovement
from .serializers import (
    TableSerializer, SessionSerializer, SessionCreateSerializer,
    PlayStationDeviceSerializer, CategorySerializer, ProductSerializer,
    SessionProductSerializer, SessionProductCreateSerializer, ReceiptSerializer,
    StockMovementSerializer, StockMovementCreateSerializer, StockReportSerializer,
    QuickStockUpdateSerializer
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Kategorilere göre ürünleri listele"""
        categories = Category.objects.prefetch_related('products').all()
        result = []
        for category in categories:
            products = ProductSerializer(category.products.filter(is_active=True), many=True).data
            result.append({
                'category': CategorySerializer(category).data,
                'products': products
            })
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def stock_report(self, request):
        """Stok raporu"""
        products = Product.objects.filter(is_active=True).select_related('category')
        
        # Filtreleme
        category_id = request.query_params.get('category')
        stock_status = request.query_params.get('stock_status')
        
        if category_id:
            products = products.filter(category_id=category_id)
        
        if stock_status == 'low':
            products = products.filter(current_stock__lte=F('min_stock_level'))
        elif stock_status == 'out':
            products = products.filter(current_stock=0)
        elif stock_status == 'normal':
            products = products.filter(current_stock__gt=F('min_stock_level'))
        
        # Rapor verisi oluştur
        report_data = []
        for product in products:
            report_data.append({
                'category_name': product.category.name,
                'product_name': product.name,
                'current_stock': product.current_stock,
                'min_stock_level': product.min_stock_level,
                'stock_status': product.stock_status,
                'unit_price': product.price,
                'stock_value': product.current_stock * product.price
            })
        
        return Response(report_data)
    
    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        """Düşük stok uyarıları"""
        low_stock_products = Product.objects.filter(
            is_active=True,
            current_stock__lte=F('min_stock_level')
        ).select_related('category')
        
        alerts = []
        for product in low_stock_products:
            alerts.append({
                'id': product.id,
                'name': product.name,
                'category': product.category.name,
                'current_stock': product.current_stock,
                'min_stock_level': product.min_stock_level,
                'status': product.stock_status,
                'urgency': 'critical' if product.is_out_of_stock else 'warning'
            })
        
        return Response({
            'total_alerts': len(alerts),
            'critical_count': len([a for a in alerts if a['urgency'] == 'critical']),
            'warning_count': len([a for a in alerts if a['urgency'] == 'warning']),
            'alerts': alerts
        })

class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StockMovementCreateSerializer
        return StockMovementSerializer
    
    def perform_create(self, serializer):
        """Stok hareketi oluştur ve ürün stokunu güncelle"""
        movement = serializer.save(created_by=self.request.user)
        
        # Ürün stokunu güncelle
        product = movement.product
        movement.old_stock = product.current_stock
        movement.new_stock = product.current_stock + movement.quantity
        movement.save()
        
        product.current_stock = movement.new_stock
        product.save()
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Toplu stok güncellemesi"""
        serializer = QuickStockUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        products_data = serializer.validated_data['products']
        movement_type = serializer.validated_data['movement_type']
        supplier = serializer.validated_data.get('supplier', '')
        notes = serializer.validated_data.get('notes', '')
        
        created_movements = []
        
        for item in products_data:
            product_id = int(item['product_id'])
            quantity = int(item['quantity'])
            unit_cost = item.get('unit_cost')
            
            product = Product.objects.get(id=product_id)
            
            # Çıkış hareketleri için negatif yap
            if movement_type in ['out', 'waste', 'sale']:
                quantity = -abs(quantity)
            
            # Stok hareketi oluştur
            movement = StockMovement.objects.create(
                product=product,
                movement_type=movement_type,
                quantity=quantity,
                old_stock=product.current_stock,
                new_stock=product.current_stock + quantity,
                unit_cost=unit_cost,
                supplier=supplier,
                notes=notes,
                created_by=request.user
            )
            
            # Ürün stokunu güncelle
            product.current_stock = movement.new_stock
            product.save()
            
            created_movements.append(movement)
        
        return Response({
            'message': f'{len(created_movements)} ürün için stok güncellendi',
            'movements': StockMovementSerializer(created_movements, many=True).data
        })
    
    @action(detail=False, methods=['get'])
    def product_history(self, request):
        """Belirli bir ürünün stok geçmişi"""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response({'error': 'product_id parametresi gerekli'}, status=400)
        
        movements = StockMovement.objects.filter(
            product_id=product_id
        ).order_by('-created_at')[:50]  # Son 50 hareket
        
        return Response(StockMovementSerializer(movements, many=True).data)

class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    
    @action(detail=True, methods=['post'])
    def start_session(self, request, pk=None):
        """Masaya yeni seans başlat"""
        table = self.get_object()
        
        # Zaten aktif seans var mı kontrol et
        if table.current_session:
            return Response(
                {'error': 'Bu masada zaten aktif bir seans var'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Masa müsait mi kontrol et
        if not table.is_available:
            return Response(
                {'error': 'Masa şu anda müsait değil'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Yeni seans oluştur
        session = Session.objects.create(
            table=table,
            user_id=1,  # Varsayılan admin kullanıcısı
            notes=request.data.get('notes', '')
        )
        
        # Masanın durumunu değiştir
        table.status = 'occupied'
        table.save()
        
        return Response({
            'message': 'Seans başlatıldı',
            'session_id': session.id,
            'table': TableSerializer(table).data
        })
    
    @action(detail=True, methods=['post'])
    def stop_session(self, request, pk=None):
        """Aktif seansı sonlandır"""
        table = self.get_object()
        session = table.current_session
        
        if not session:
            return Response(
                {'error': 'Bu masada aktif seans yok'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Seansı sonlandır
        session.end_time = timezone.now()
        session.calculate_final_amounts()
        
        # Masanın durumunu değiştir
        table.status = 'available'
        table.save()
        
        return Response({
            'message': 'Seans sonlandırıldı',
            'session': SessionSerializer(session).data,
            'total_amount': float(session.total_amount),
            'gaming_amount': float(session.gaming_amount),
            'products_amount': float(session.products_amount),
            'duration_minutes': session.duration_minutes
        })
    
    @action(detail=True, methods=['post'])
    def add_product(self, request, pk=None):
        """Aktif seansa ürün ekle"""
        table = self.get_object()
        session = table.current_session
        
        if not session:
            return Response(
                {'error': 'Bu masada aktif seans yok'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Geçersiz ürün'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Stok kontrolü
        if product.current_stock < quantity:
            return Response(
                {'error': f'{product.name} için yeterli stok yok. Mevcut: {product.current_stock}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ürünü seansa ekle (stok otomatik azalacak)
        try:
            session_product = SessionProduct.objects.create(
                session=session,
                product=product,
                quantity=quantity
            )
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': f'{product.name} sepete eklendi',
            'product_name': product.name,
            'session_product': SessionProductSerializer(session_product).data,
            'session': SessionSerializer(session).data
        })
    
    @action(detail=True, methods=['post'])
    def remove_product(self, request, pk=None):
        """Aktif seanstan ürün çıkar"""
        table = self.get_object()
        session = table.current_session
        
        if not session:
            return Response(
                {'error': 'Bu masada aktif seans yok'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session_product_id = request.data.get('session_product_id')
        
        try:
            session_product = SessionProduct.objects.get(
                id=session_product_id, 
                session=session
            )
            product_name = session_product.product.name
            session_product.delete()  # Stok otomatik geri eklenecek
            
            return Response({
                'message': f'{product_name} sepetten çıkarıldı',
                'product_name': product_name,
                'session': SessionSerializer(session).data
            })
        except SessionProduct.DoesNotExist:
            return Response(
                {'error': 'Geçersiz ürün'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def create_receipt(self, request, pk=None):
        """Seans için fiş kes"""
        table = self.get_object()
        session = table.current_session
        
        if not session:
            return Response(
                {'error': 'Bu masada aktif seans yok'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eğer seans bitmemişse bitir
        if not session.end_time:
            session.end_time = timezone.now()
            session.calculate_final_amounts()
        
        # Fiş oluştur
        receipt = Receipt.objects.create(
            session=session,
            issued_by_id=1  # Varsayılan admin kullanıcısı
        )
        
        # Seansı ödendi olarak işaretle
        session.is_paid = True
        session.save()
        
        return Response({
            'message': 'Fiş kesildi',
            'receipt': ReceiptSerializer(receipt).data,
            'table_name': table.name,
            'user_name': session.user.username,
            'start_time': session.start_time,
            'end_time': session.end_time
        })
    
    @action(detail=True, methods=['post'])
    def reset_table(self, request, pk=None):
        """Masayı resetle"""
        table = self.get_object()
        
        # Aktif seans varsa ve ödenmişse resetle
        if table.current_session:
            session = table.current_session
            if not session.is_paid:
                return Response(
                    {'error': 'Seans henüz ödenmedi. Önce fiş kesin.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            session.is_reset = True
            session.save()
        
        # Masayı müsait yap
        table.status = 'available'
        table.save()
        
        return Response({
            'message': 'Masa resetlendi',
            'table': TableSerializer(table).data
        })
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Dashboard için istatistikler"""
        today = timezone.now().date()
        
        # Temel sayılar
        total_tables = Table.objects.count()
        available_tables = Table.objects.filter(status='available').count()
        occupied_tables = Table.objects.filter(status='occupied').count()
        active_sessions = Session.objects.filter(end_time__isnull=True).count()
        
        # Bugünkü gelir
        today_sessions = Session.objects.filter(start_time__date=today)
        today_revenue = today_sessions.filter(
            end_time__isnull=False
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        
        today_sessions_count = today_sessions.count()
        
        # Stok istatistikleri
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_products = Product.objects.filter(
            is_active=True,
            current_stock__lte=F('min_stock_level')
        ).count()
        out_of_stock_products = Product.objects.filter(
            is_active=True,
            current_stock=0
        ).count()
        
        # Toplam stok değeri
        total_stock_value = Product.objects.filter(
            is_active=True
        ).aggregate(
            total=Sum(F('current_stock') * F('price'))
        )['total'] or Decimal('0')
        
        stats = {
            'total_tables': total_tables,
            'available_tables': available_tables,
            'occupied_tables': occupied_tables,
            'active_sessions': active_sessions,
            'today_revenue': today_revenue,
            'today_sessions': today_sessions_count,
            
            # Stok bilgileri
            'total_products': total_products,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock_products,
            'total_stock_value': total_stock_value
        }
        
        return Response(stats)

class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SessionCreateSerializer
        return SessionSerializer
    
    def perform_create(self, serializer):
        serializer.save(user_id=1)  # Varsayılan admin kullanıcısı

class SessionProductViewSet(viewsets.ModelViewSet):
    queryset = SessionProduct.objects.all()
    serializer_class = SessionProductSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SessionProductCreateSerializer
        return SessionProductSerializer

class ReceiptViewSet(viewsets.ModelViewSet):
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer

class PlayStationDeviceViewSet(viewsets.ModelViewSet):
    queryset = PlayStationDevice.objects.all()
    serializer_class = PlayStationDeviceSerializer