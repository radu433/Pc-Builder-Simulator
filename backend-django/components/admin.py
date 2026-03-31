from django.contrib import admin
from .models import CPU, GPU, Motherboard, RAM, PSU, Case, Cooler

admin.site.register(CPU)
admin.site.register(GPU)
admin.site.register(Motherboard)
admin.site.register(RAM)
admin.site.register(PSU)
admin.site.register(Case)
admin.site.register(Cooler)