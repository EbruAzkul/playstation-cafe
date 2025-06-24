from rest_framework import serializers
from .models import Table, Session, PlayStationDevice

class TableSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    current_session = serializers.SerializerMethodField()
    
    class Meta:
        model = Table
        fields = ['id', 'name', 'playstation_ip', 'hourly_rate', 'status', 
                 'status_display', 'is_available', 'current_session', 'created_at']
    
    def get_current_session(self, obj):
        session = obj.current_session
        if session:
            return {
                'id': session.id,
                'start_time': session.start_time,
                'duration_minutes': session.duration_minutes,
                'current_amount': float(session.current_amount),
                'user': session.user.username
            }
        return None

class SessionSerializer(serializers.ModelSerializer):
    table_name = serializers.CharField(source='table.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    current_amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    
    class Meta:
        model = Session
        fields = ['id', 'table', 'table_name', 'user', 'user_name', 
                 'start_time', 'end_time', 'duration_minutes', 'current_amount',
                 'total_amount', 'notes', 'created_at']

class SessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['table', 'notes']

class PlayStationDeviceSerializer(serializers.ModelSerializer):
    table_name = serializers.CharField(source='table.name', read_only=True)
    
    class Meta:
        model = PlayStationDevice
        fields = ['id', 'table', 'table_name', 'device_type', 'mac_address', 
                 'is_online', 'last_seen']