from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from .models import Table, Session, PlayStationDevice, Category, Product, SessionProduct, Receipt
from .serializers import (
    TableSerializer, SessionSerializer, SessionCreateSerializer,
    PlayStationDeviceSerializer, CategorySerializer, ProductSerializer,
    SessionProductSerializer, SessionProductCreateSerializer, ReceiptSerializer
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
        
        # Ürünü seansa ekle
        session_product = SessionProduct.objects.create(
            session=session,
            product=product,
            quantity=quantity
        )
        
        return Response({
            'message': f'{product.name} sepete eklendi',
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
            session_product.delete()
            
            return Response({
                'message': f'{product_name} sepetten çıkarıldı',
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
            'receipt': ReceiptSerializer(receipt).data
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
        
        stats = {
            'total_tables': total_tables,
            'available_tables': available_tables,
            'occupied_tables': occupied_tables,
            'active_sessions': active_sessions,
            'today_revenue': today_revenue,
            'today_sessions': today_sessions_count
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