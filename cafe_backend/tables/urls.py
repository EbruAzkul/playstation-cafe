from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TableViewSet, SessionViewSet, PlayStationDeviceViewSet,
    CategoryViewSet, ProductViewSet, SessionProductViewSet, ReceiptViewSet
)

router = DefaultRouter()
router.register(r'tables', TableViewSet)
router.register(r'sessions', SessionViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'session-products', SessionProductViewSet)
router.register(r'receipts', ReceiptViewSet)
router.register(r'playstation', PlayStationDeviceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]