from django.contrib import admin
# Importăm toate modelele pe care le-am creat anterior
from .models import CPU, GPU, Motherboard, RAM, PSU, Case, Cooler

# Le înregistrăm pe rând ca să apară în panoul de control
admin.site.register(CPU)
admin.site.register(GPU)
admin.site.register(Motherboard)
admin.site.register(RAM)
admin.site.register(PSU)
admin.site.register(Case)
admin.site.register(Cooler)