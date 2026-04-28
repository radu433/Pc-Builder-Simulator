from django.shortcuts import render
from rest_framework import viewsets, filters

# Create your views here.

from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics
from .models import CPU, GPU, RAM, Storage, Motherboard, PSU, Case,Cooler,SaveBuild
from .serializers import CPUSerializer, GPUSerializer, RAMSerializer, StorageSerializer, MotherboardSerializer, PSU, CaseSerializer,CoolerSerializer,PSUSerializer,SaveBuildSerializer

class CPUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CPU.objects.all()
    serializer_class = CPUSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']
    permission_classes = [AllowAny]
    
class GPUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GPU.objects.all()
    serializer_class = GPUSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']
    permission_classes = [AllowAny]

class RAMViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RAM.objects.all()
    serializer_class = RAMSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']
    permission_classes = [AllowAny]

class StorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']
    permission_classes = [AllowAny]

class MotherboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Motherboard.objects.all()
    serializer_class = MotherboardSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']
    permission_classes = [AllowAny]

class PSUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PSU.objects.all()
    serializer_class = PSUSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']
    permission_classes = [AllowAny]

class CaseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']
    permission_classes = [AllowAny]

class CoolerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cooler.objects.all()
    serializer_class = CoolerSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nume','brand','serie']
    permission_classes = [AllowAny]

class SaveBuildListCreateView(viewsets.ModelViewSet):
    serializer_class = SaveBuildSerializer
    permission_classes = [IsAuthenticated]

    #Cand Vue cere lista, ii dam DOAR pc-urile lui
    def get_queryset(self):
        return SaveBuild.objects.filter(user=self.request.user)
    #pt salvare de pc-uri
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)