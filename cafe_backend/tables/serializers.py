from rest_framework import serializers
from .models import Table, Session, PlayStationDevice, Category, Product, SessionProduct, Receipt, StockMovement

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'product_count', 'created_at']
    
    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_status = serializers.CharField(read_only=True)
    stock_status_display = serializers.CharField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'category_name', 'price', 'is_active', 
                 'current_stock', 'min_stock_level', 'max_stock_level', 'stock_unit',
                 'stock_status', 'stock_status_display', 'is_low_stock', 'is_out_of_stock',
                 'created_at']

class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = ['id', 'product', 'product_name', 'movement_type', 'movement_type_display',
                 'quantity', 'old_stock', 'new_stock', 'unit_cost', 'total_cost',
                 'supplier', 'notes', 'created_by', 'created_by_name', 'created_at']

class StockMovementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'unit_cost', 'supplier', 'notes']
    
    def validate(self, data):
        product = data['product']
        quantity = data['quantity']
        movement_type = data['movement_type']
        
        # Stok çıkışı kontrolü
        if movement_type in ['out', 'waste'] and quantity > 0:
            quantity = -quantity  # Çıkış için negatif yap
            data['quantity'] = quantity
        
        # Yeterli stok kontrolü
        if quantity < 0 and product.current_stock < abs(quantity):
            raise serializers.ValidationError(
                f'{product.name} için yeterli stok yok. Mevcut: {product.current_stock}, İstenen: {abs(quantity)}'
            )
        
        return data

class SessionProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    
    class Meta:
        model = SessionProduct
        fields = ['id', 'product', 'product_name', 'category_name', 'quantity', 
                 'unit_price', 'total_price', 'added_at']

class SessionProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionProduct
        fields = ['product', 'quantity']
    
    def validate(self, data):
        product = data['product']
        quantity = data['quantity']
        
        # Stok kontrolü
        if product.current_stock < quantity:
            raise serializers.ValidationError(
                f'{product.name} için yeterli stok yok. Mevcut: {product.current_stock}, İstenen: {quantity}'
            )
        
        # Aktif ürün kontrolü
        if not product.is_active:
            raise serializers.ValidationError(f'{product.name} aktif değil.')
        
        return data

class TableSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    current_session = serializers.SerializerMethodField()
    
    class Meta:
        model = Table
        fields = ['id', 'name', 'playstation_ip', 'hourly_rate', 'opening_fee', 'status', 
                 'status_display', 'is_available', 'current_session', 'created_at']
    
    def get_current_session(self, obj):
        session = obj.current_session
        if session:
            return {
                'id': session.id,
                'start_time': session.start_time,
                'duration_minutes': session.duration_minutes,
                'gaming_amount': float(session.current_gaming_amount),
                'products_amount': float(session.products_amount),
                'total_amount': float(session.current_total_amount),
                'user': session.user.username,
                'is_paid': session.is_paid,
                'products': SessionProductSerializer(session.products.all(), many=True).data
            }
        return None

class SessionSerializer(serializers.ModelSerializer):
    table_name = serializers.CharField(source='table.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    current_gaming_amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    current_total_amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    products = SessionProductSerializer(many=True, read_only=True)
    
    class Meta:
        model = Session
        fields = ['id', 'table', 'table_name', 'user', 'user_name', 
                 'start_time', 'end_time', 'duration_minutes', 
                 'opening_fee', 'hourly_rate', 'gaming_amount', 'products_amount', 'total_amount',
                 'current_gaming_amount', 'current_total_amount',
                 'notes', 'is_paid', 'is_reset', 'products', 'created_at']

class SessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['table', 'notes']

class ReceiptSerializer(serializers.ModelSerializer):
    session_data = SessionSerializer(source='session', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.username', read_only=True)
    
    class Meta:
        model = Receipt
        fields = ['id', 'receipt_number', 'session', 'session_data', 
                 'issued_by', 'issued_by_name', 'issued_at']

class PlayStationDeviceSerializer(serializers.ModelSerializer):
    table_name = serializers.CharField(source='table.name', read_only=True)
    
    class Meta:
        model = PlayStationDevice
        fields = ['id', 'table', 'table_name', 'device_type', 'mac_address', 
                 'is_online', 'last_seen']

# Dashboard için özet serializer
class DashboardStatsSerializer(serializers.Serializer):
    total_tables = serializers.IntegerField()
    available_tables = serializers.IntegerField()
    occupied_tables = serializers.IntegerField()
    active_sessions = serializers.IntegerField()
    today_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    today_sessions = serializers.IntegerField()
    
    # Stok istatistikleri
    total_products = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    out_of_stock_products = serializers.IntegerField()
    total_stock_value = serializers.DecimalField(max_digits=12, decimal_places=2)

# Stok raporu için serializer
class StockReportSerializer(serializers.Serializer):
    category_name = serializers.CharField()
    product_name = serializers.CharField()
    current_stock = serializers.IntegerField()
    min_stock_level = serializers.IntegerField()
    stock_status = serializers.CharField()
    unit_price = serializers.DecimalField(max_digits=6, decimal_places=2)
    stock_value = serializers.DecimalField(max_digits=10, decimal_places=2)

# Hızlı stok işlemleri için serializer
class QuickStockUpdateSerializer(serializers.Serializer):
    products = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    movement_type = serializers.ChoiceField(choices=StockMovement.MOVEMENT_TYPES)
    supplier = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_products(self, value):
        """Ürün listesi validasyonu"""
        if not value:
            raise serializers.ValidationError("En az bir ürün belirtilmelidir.")
        
        for item in value:
            if 'product_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError("Her ürün için product_id ve quantity gereklidir.")
            
            try:
                product_id = int(item['product_id'])
                quantity = int(item['quantity'])
            except (ValueError, TypeError):
                raise serializers.ValidationError("Geçersiz ürün ID'si veya miktar.")
            
            # Ürün varlık kontrolü
            if not Product.objects.filter(id=product_id, is_active=True).exists():
                raise serializers.ValidationError(f"ID {product_id} ile ürün bulunamadı veya aktif değil.")
        
        return value