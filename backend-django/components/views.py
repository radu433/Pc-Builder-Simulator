from django.shortcuts import render
from rest_framework import viewsets, filters

# Create your views here.

from rest_framework import viewsets
from .models import CPU, GPU, RAM, Storage, Motherboard, PSU, Case,Cooler
from .serializers import CPUSerializer, GPUSerializer, RAMSerializer, StorageSerializer, MotherboardSerializer, PSU, CaseSerializer,CoolerSerializer,PSUSerializer

class CPUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CPU.objects.all()
    serializer_class = CPUSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']

class GPUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GPU.objects.all()
    serializer_class = GPUSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']

class RAMViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RAM.objects.all()
    serializer_class = RAMSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']

class StorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']

class MotherboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Motherboard.objects.all()
    serializer_class = MotherboardSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']

class PSUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PSU.objects.all()
    serializer_class = PSUSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']

class CaseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']

class CoolerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cooler.objects.all()
    serializer_class = CoolerSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']