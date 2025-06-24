from django.contrib import admin
from .models import Table, Session, PlayStationDevice

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'hourly_rate', 'playstation_ip', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'playstation_ip']
    list_editable = ['status', 'hourly_rate']
    ordering = ['name']

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['table', 'user', 'start_time', 'end_time', 'duration_minutes', 'total_amount']
    list_filter = ['start_time', 'end_time', 'table']
    search_fields = ['table__name', 'user__username']
    readonly_fields = ['duration_minutes', 'current_amount']
    ordering = ['-start_time']
    
    def duration_minutes(self, obj):
        return f"{obj.duration_minutes} dakika"
    duration_minutes.short_description = 'Süre'

@admin.register(PlayStationDevice)
class PlayStationDeviceAdmin(admin.ModelAdmin):
    list_display = ['table', 'device_type', 'mac_address', 'is_online', 'last_seen']
    list_filter = ['device_type', 'is_online']
    search_fields = ['table__name', 'mac_address']
    list_editable = ['is_online']