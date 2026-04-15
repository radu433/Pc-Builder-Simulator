from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CPUViewSet, GPUViewSet, RAMViewSet, StorageViewSet, MotherboardViewSet, PSUViewSet, CaseViewSet,CoolerViewSet

router = DefaultRouter()
router.register(r'cpus', CPUViewSet)
router.register(r'gpus', GPUViewSet)
router.register(r'rams', RAMViewSet)
router.register(r'storages', StorageViewSet)
router.register(r'motherboards', MotherboardViewSet)
router.register(r'psus', PSUViewSet)
router.register(r'cases', CaseViewSet)
router.register(r'coolers', CoolerViewSet)

urlpatterns = [
    path('', include(router.urls)),
]