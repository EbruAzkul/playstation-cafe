from rest_framework import serializers
from .models import Table, Session, PlayStationDevice, Category, Product, SessionProduct, Receipt

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'product_count', 'created_at']
    
    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'category_name', 'price', 'is_active', 'created_at']

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
                'is_paid': session.is_paid
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