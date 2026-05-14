import django_filters
from django.db.models import Q
from .models import CPU, GPU, RAM, Storage, Motherboard, PSU, Case, Cooler

# Filtrul inteligent pentru checkbox-uri
class CharInFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        # Dacă nu s-a bifat nimic, returnăm toate rezultatele
        if not value:
            return qs
            
        valori = [v.strip() for v in value.split(',')]
        q_objects = Q()
        
        for val in valori:
            # 1. Căutare normală pentru procesoare gen "AM4", "AM5"
            q_objects |= Q(**{f"{self.field_name}__icontains": val})
            
            # 2. Dacă e socket Intel (conține "LGA"), extragem strict numărul și căutăm după el
            if "LGA" in val.upper():
                doar_numarul = ''.join([c for c in val if c.isdigit()])
                if doar_numarul:
                    # Va adăuga o căutare de tipul: socket__icontains="1700"
                    q_objects |= Q(**{f"{self.field_name}__icontains": doar_numarul})

        return qs.filter(q_objects)


# Clasa de bază (Preț și Stoc - funcționează la fel peste tot)
class BaseComponentFilter(django_filters.FilterSet):
    min_pret = django_filters.NumberFilter(field_name="pret", lookup_expr='gte')
    max_pret = django_filters.NumberFilter(field_name="pret", lookup_expr='lte')
    brand = django_filters.CharFilter(field_name="brand", lookup_expr='iexact')
    in_stock = django_filters.BooleanFilter(field_name="stoc", method='filter_in_stock')

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stoc=True)
        return queryset


# --- FILTRELE PE CATEGORII ---

class CPUFilter(BaseComponentFilter):
    producator = django_filters.CharFilter(field_name="brand", lookup_expr='iexact')
    socket = CharInFilter(field_name="socket") # Va folosi filtrul de mai sus

    class Meta:
        model = CPU
        fields = []


class MotherboardFilter(BaseComponentFilter):
    socket = CharInFilter(field_name="socket") # Va folosi filtrul de mai sus
    tip_ram = django_filters.CharFilter(field_name="tip_memorie", lookup_expr='icontains')
    format = django_filters.CharFilter(field_name="format", lookup_expr='icontains')

    class Meta:
        model = Motherboard
        fields = []


class GPUFilter(BaseComponentFilter):
    producator = django_filters.CharFilter(field_name="brand", lookup_expr='iexact')
    producator_chipset = django_filters.CharFilter(field_name="chipset_brand", lookup_expr='iexact')
    memorie = django_filters.NumberFilter(field_name="vram_gb") 

    class Meta:
        model = GPU
        fields = []


class RAMFilter(BaseComponentFilter):
    tip = django_filters.CharFilter(field_name="tip_memorie", lookup_expr='icontains')
    capacitate = django_filters.NumberFilter(field_name="capacitate_totala_gb")

    class Meta:
        model = RAM
        fields = []


class StorageFilter(BaseComponentFilter):
    tip = django_filters.CharFilter(field_name="tip", lookup_expr='icontains')
    capacitate = django_filters.NumberFilter(field_name="capacitate_gb")

    class Meta:
        model = Storage
        fields = []


class PSUFilter(BaseComponentFilter):
    putere = django_filters.NumberFilter(field_name="putere_w", lookup_expr='gte') 
    certificare = django_filters.CharFilter(field_name="certificare", lookup_expr='icontains')

    class Meta:
        model = PSU
        fields = []


class CaseFilter(BaseComponentFilter):
    tip_carcasa = django_filters.CharFilter(field_name="tip_carcasa", lookup_expr='iexact')

    class Meta:
        model = Case
        fields = []


class CoolerFilter(BaseComponentFilter):
    socket = CharInFilter(field_name="socket_suportate")
    tip_racire = django_filters.CharFilter(field_name="tip_racire", lookup_expr='icontains')

    class Meta:
        model = Cooler
        fields = []