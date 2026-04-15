from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets
from .models import CPU, GPU, RAM, Storage, Motherboard, PSU, Case,Cooler
from .serializers import CPUSerializer, GPUSerializer, RAMSerializer, StorageSerializer, MotherboardSerializer, PSU, CaseSerializer,CoolerSerializer,PSUSerializer

class CPUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CPU.objects.all()
    serializer_class = CPUSerializer

class GPUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GPU.objects.all()
    serializer_class = GPUSerializer

class RAMViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RAM.objects.all()
    serializer_class = RAMSerializer

class StorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer

class MotherboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Motherboard.objects.all()
    serializer_class = MotherboardSerializer

class PSUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PSU.objects.all()
    serializer_class = PSUSerializer

class CaseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer

class CoolerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cooler.objects.all()
    serializer_class = CoolerSerializer