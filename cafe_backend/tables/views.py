from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Table, Session, PlayStationDevice
from .serializers import (
    TableSerializer, SessionSerializer, SessionCreateSerializer,
    PlayStationDeviceSerializer
)

class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    # permission_classes = [IsAuthenticated]  # Geçici olarak kaldırıldı
    
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
        
        # Yeni seans oluştur (geçici olarak user_id=1)
        session = Session.objects.create(
            table=table,
            user_id=1,  # Varsayılan admin kullanıcısı
            notes=request.data.get('notes', '')
        )
        
        # Masanın durumunu değiştir
        table.status = 'occupied'
        table.save()
        
        # PlayStation'ı aç (sonradan ekleyeceğiz)
        # control_playstation(table.playstation_ip, 'on')
        
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
        session.calculate_total()
        
        # Masanın durumunu değiştir
        table.status = 'available'
        table.save()
        
        # PlayStation'ı kapat (sonradan ekleyeceğiz)
        # control_playstation(table.playstation_ip, 'off')
        
        return Response({
            'message': 'Seans sonlandırıldı',
            'session': SessionSerializer(session).data,
            'total_amount': float(session.total_amount),
            'duration_minutes': session.duration_minutes
        })
    
    @action(detail=True, methods=['get'])
    def current_session(self, request, pk=None):
        """Masanın aktif seansını getir"""
        table = self.get_object()
        session = table.current_session
        
        if not session:
            return Response({'session': None})
        
        return Response({
            'session': SessionSerializer(session).data
        })
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Müsait masaları listele"""
        tables = self.queryset.filter(status='available')
        serializer = self.get_serializer(tables, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def occupied(self, request):
        """Dolu masaları listele"""
        tables = self.queryset.filter(status='occupied')
        serializer = self.get_serializer(tables, many=True)
        return Response(serializer.data)

class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    # permission_classes = [IsAuthenticated]  # Geçici olarak kaldırıldı
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SessionCreateSerializer
        return SessionSerializer
    
    def perform_create(self, serializer):
        serializer.save(user_id=1)  # Varsayılan admin kullanıcısı
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Aktif seansları listele"""
        sessions = self.queryset.filter(end_time__isnull=True)
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Bugünkü seansları listele"""
        today = timezone.now().date()
        sessions = self.queryset.filter(start_time__date=today)
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)

class PlayStationDeviceViewSet(viewsets.ModelViewSet):
    queryset = PlayStationDevice.objects.all()
    serializer_class = PlayStationDeviceSerializer
    # permission_classes = [IsAuthenticated]  # Geçici olarak kaldırıldı
    
    @action(detail=True, methods=['post'])
    def power_on(self, request, pk=None):
        """PlayStation'ı aç"""
        device = self.get_object()
        
        # PlayStation kontrolü (sonradan ekleyeceğiz)
        # success = control_playstation(device.table.playstation_ip, 'on')
        
        # Şimdilik mock response
        device.is_online = True
        device.last_seen = timezone.now()
        device.save()
        
        return Response({
            'message': f'{device.device_type} açıldı',
            'device': self.get_serializer(device).data
        })
    
    @action(detail=True, methods=['post'])
    def power_off(self, request, pk=None):
        """PlayStation'ı kapat"""
        device = self.get_object()
        
        # PlayStation kontrolü (sonradan ekleyeceğiz)
        # success = control_playstation(device.table.playstation_ip, 'off')
        
        # Şimdilik mock response
        device.is_online = False
        device.save()
        
        return Response({
            'message': f'{device.device_type} kapatıldı',
            'device': self.get_serializer(device).data
        })