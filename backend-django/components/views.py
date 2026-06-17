from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend # NOU: Importăm backend-ul de filtrare

from .models import CPU, GPU, RAM, Storage, Motherboard, PSU, Case, Cooler, SaveBuild
from .serializers import (CPUSerializer, GPUSerializer, RAMSerializer, StorageSerializer,
                          MotherboardSerializer, CaseSerializer, CoolerSerializer,
                          PSUSerializer, SaveBuildSerializer)

# NOU: Importăm filtrele noastre custom
from .filters import (CPUFilter, GPUFilter, RAMFilter, StorageFilter, 
                      MotherboardFilter, PSUFilter, CaseFilter, CoolerFilter)

# ── Paginare 50 produse/pagină ──
class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class CPUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CPU.objects.all()
    serializer_class = CPUSerializer
    # Am adăugat DjangoFilterBackend
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CPUFilter # Legăm de filtrul specific
    search_fields = ['nume', 'brand', 'serie']
    ordering_fields = ['pret', 'nume']
    ordering = ['nume']
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class GPUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GPU.objects.all()
    serializer_class = GPUSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = GPUFilter
    search_fields = ['nume', 'brand', 'serie']
    ordering_fields = ['pret', 'nume']
    ordering = ['nume']
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class RAMViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RAM.objects.all()
    serializer_class = RAMSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RAMFilter
    search_fields = ['nume', 'brand', 'serie']
    ordering_fields = ['pret', 'nume']
    ordering = ['nume']
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class StorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StorageFilter
    search_fields = ['nume', 'brand', 'serie']
    ordering_fields = ['pret', 'nume']
    ordering = ['nume']
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class MotherboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Motherboard.objects.all()
    serializer_class = MotherboardSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MotherboardFilter
    search_fields = ['nume', 'brand', 'serie']
    ordering_fields = ['pret', 'nume']
    ordering = ['nume']
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class PSUViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PSU.objects.all()
    serializer_class = PSUSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PSUFilter
    search_fields = ['nume', 'brand', 'serie']
    ordering_fields = ['pret', 'nume']
    ordering = ['nume']
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class CaseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CaseFilter
    search_fields = ['nume', 'brand', 'serie']
    ordering_fields = ['pret', 'nume']
    ordering = ['nume']
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class CoolerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cooler.objects.all()
    serializer_class = CoolerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CoolerFilter
    search_fields = ['nume', 'brand', 'serie']
    ordering_fields = ['pret', 'nume']
    ordering = ['nume']
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class SaveBuildListCreateView(viewsets.ModelViewSet):
    serializer_class = SaveBuildSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SaveBuild.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)