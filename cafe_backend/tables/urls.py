from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TableViewSet, SessionViewSet, PlayStationDeviceViewSet

router = DefaultRouter()
router.register(r'tables', TableViewSet)
router.register(r'sessions', SessionViewSet)
router.register(r'playstation', PlayStationDeviceViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]