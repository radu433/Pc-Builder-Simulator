from django.db import models

class ComponentaBase(models.Model):
    nume = models.CharField(max_length=300)
    brand = models.CharField(max_length=200)
    pret = models.DecimalField(max_digits=10, decimal_places=2)
    magazin = models.CharField(max_length=100)
    url_produs = models.URLField(max_length=500)
    imagine_url = models.URLField(max_length=500, null=True, blank=True)
    stoc = models.BooleanField(default=True)
    regiune = models.CharField(max_length=50, default='Romania')
    ultima_actualizare = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class GPU(ComponentaBase):
    serie = models.CharField(max_length=200)
    model_chipset = models.CharField(max_length=200)
    vram_gb = models.IntegerField()
    consum_tdp = models.IntegerField()
    lungime_mm = models.IntegerField()
    latime_mm = models.IntegerField()
    inaltime_mm = models.IntegerField()

    def __str__(self):
        return self.nume

class CPU(ComponentaBase):
    socket = models.CharField(max_length=100)
    serie = models.CharField(max_length=200)
    nuclee = models.IntegerField()
    frecventa_ghz = models.DecimalField(max_digits=4, decimal_places=2)
    consum_tdp = models.IntegerField()

    def __str__(self):
        return self.nume

class Motherboard(ComponentaBase):
    socket = models.CharField(max_length=100)
    chipset = models.CharField(max_length=100)
    format = models.CharField(max_length=50)
    tip_memorie = models.CharField(max_length=50)
    are_wifi = models.BooleanField(default=False)
    are_bluetooth = models.BooleanField(default=False)
    porturi_io = models.JSONField(default=dict)

    def __str__(self):
        return self.nume

class RAM(ComponentaBase):
    capacitate_totala_gb = models.IntegerField()
    numar_module = models.IntegerField(default=2)
    tip_memorie = models.CharField(max_length=50)
    frecventa_mhz = models.IntegerField()
    latenta_cl = models.IntegerField()
    inaltime_mm = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.nume

class PSU(ComponentaBase):
    putere_w = models.IntegerField()
    certificare = models.CharField(max_length=150)
    este_modulara = models.BooleanField(default=False)
    lungime_mm = models.IntegerField(default=150)

    def __str__(self):
        return self.nume

class Carcasa(ComponentaBase):
    TIP_CARCASA_CHOICES = [
        ('MID', 'Mid Tower'),
        ('FULL', 'Full Tower'),
        ('MINI', 'Mini Tower'),
        ('AQ', 'Aquarium'),
        ('SFF', 'Small Form Factor'),
    ]
    tip_carcasa = models.CharField(max_length=10, choices=TIP_CARCASA_CHOICES)
    formate_suportate = models.JSONField(default=list)
    include_sursa = models.BooleanField(default=False)
    pozitie_sursa = models.CharField(max_length=100, default="Jos Spate")
    inaltime_mm = models.IntegerField()
    lungime_mm = models.IntegerField()
    latime_mm = models.IntegerField()

    def __str__(self):
        return self.nume

class Cooler(ComponentaBase):
    tip_racire = models.CharField(max_length=50)
    socket_suportate = models.JSONField(default=list)
    inaltime_mm = models.IntegerField(null=True, blank=True)
    lungime_radiator_mm = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.nume