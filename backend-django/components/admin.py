from django.contrib import admin
from .models import CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage, Monitor, Fan, NetworkAdapter, SaveBuild

# 1. Configurare pentru PLĂCI VIDEO
@admin.register(GPU)
class GPUAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'stoc', 'consum_tdp')
    search_fields = ('nume', 'brand', 'part_number', 'model_chipset')
    list_filter = ('brand', 'stoc', 'regiune')

# 2. Configurare pentru PROCESOARE
@admin.register(CPU)
class CPUAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'stoc', 'consum_tdp', 'socket')
    search_fields = ('nume', 'brand', 'part_number', 'socket', 'serie')
    list_filter = ('brand', 'stoc', 'socket')

# 3. Configurare pentru PLĂCI DE BAZĂ
@admin.register(Motherboard)
class MotherboardAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'socket', 'format', 'tip_memorie') # Corectat: tip_memorie
    search_fields = ('nume', 'brand', 'part_number', 'socket')
    list_filter = ('brand', 'format', 'tip_memorie') # Corectat

# 4. Configurare pentru MEMORIE RAM
@admin.register(RAM)
class RAMAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'capacitate_totala_gb', 'frecventa_mhz', 'tip_memorie') # Corectat
    search_fields = ('nume', 'brand', 'part_number', 'tip_memorie') # Corectat
    list_filter = ('brand', 'tip_memorie', 'capacitate_totala_gb') # Corectat

# 5. Configurare pentru STOCARE
@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'capacitate_gb', 'tip') # Corectat: tip
    search_fields = ('nume', 'brand', 'part_number', 'tip') # Corectat
    list_filter = ('brand', 'tip') # Corectat

# 6. Configurare pentru SURSE
@admin.register(PSU)
class PSUAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'putere_w', 'certificare')
    search_fields = ('nume', 'brand', 'part_number', 'certificare')
    list_filter = ('brand', 'certificare', 'putere_w')

# 7. Configurare pentru CARCASE
@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'tip_carcasa') # Corectat: tip_carcasa
    search_fields = ('nume', 'brand', 'part_number')
    list_filter = ('brand', 'tip_carcasa') # Corectat

# 8. Configurare pentru COOLERE
@admin.register(Cooler)
class CoolerAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'tip_racire') # Corectat: tip_racire
    search_fields = ('nume', 'brand', 'part_number', 'tip_racire') # Corectat
    list_filter = ('brand', 'tip_racire') # Corectat

# 9. COMPONENTE NOI (Monitor, Fan, Network)
@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'diagonala_inch', 'rezolutie', 'rata_refresh_hz')
    search_fields = ('nume', 'brand', 'rezolutie')
    list_filter = ('brand', 'rata_refresh_hz', 'tip_panou')

@admin.register(Fan)
class FanAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'dimensiune_mm', 'are_rgb')
    search_fields = ('nume', 'brand')
    list_filter = ('brand', 'dimensiune_mm', 'are_rgb')

@admin.register(NetworkAdapter)
class NetworkAdapterAdmin(admin.ModelAdmin):
    list_display = ('nume', 'brand', 'pret', 'interfata', 'viteza_maxima_mbps')
    search_fields = ('nume', 'brand')
    list_filter = ('brand', 'interfata')

# 10. Configurare pentru CONFIGURAȚII SALVATE
@admin.register(SaveBuild)
class SaveBuildAdmin(admin.ModelAdmin):
    list_display = ('nume', 'user', 'pret_total', 'data_salvarii')
    search_fields = ('nume', 'user__username')
    list_filter = ('data_salvarii',)
    readonly_fields = ('data_salvarii',)