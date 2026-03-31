from django.db import models

class ComponentaBase(models.Model):
    Nume = models.CharField(max_length=300)
    producator = models.CharField(max_length=200)
    pret = models.DecimalField(max_digits=10, decimal_places=2) 
    magazin = models.CharField(max_length=100)  
    url_sursa = models.URLField(max_length=500) 
    imagine_url = models.URLField(max_length=500, null=True, blank=True)
    stoc = models.BooleanField(default=True)
    regiune = models.CharField(max_length=50, default='Romania') 
    ultima_actualizare = models.DateTimeField(auto_now=True) 
    class Meta:
        abstract = True

class GPU(ComponentaBase):
    Serie=models.CharField(max_length=200)
    Model=models.CharField(max_length=200)
    Vram=models.IntegerField()
    lungime_mm = models.IntegerField()
    Usage=models.IntegerField()

    def __str__(self):
        return self.Nume

class CPU(ComponentaBase):
    Serie=models.CharField(max_length=200)
    Model=models.CharField(max_length=200)
    Viteza=models.DecimalField(max_digits=1,decimal_places=1)
    Socket=models.CharField(max_length=100)
    Usage=models.IntegerField()
    def __str__(self):
        return self.Nume
    
class PSU(ComponentaBase):
    Putere=models.IntegerField()
    Certificare=models.CharField(max_length=150)
    este_modulara = models.BooleanField(default=False)
    def __str__(self):
        return self.Nume
    
class Motherboard(ComponentaBase):
    Chipset=models.CharField(max_length=10)
    Format=models.CharField(max_length=10)
    Socket=models.CharField(max_length=50)
    Tip_memorie=models.CharField(max_length=6)
    Sloturi_mem=models.IntegerField(default=2)
    Wifi=models.BooleanField(default=False)
    Bh=models.BooleanField(default=False)
    sloturi_m2 = models.IntegerField(default=1)
    porturi_io = models.JSONField(default=dict, help_text="Ex: {'usb_3_2': 4, 'usb_c': 1, 'hdmi': 1}")
    
    def __str__(self):
       return self.Nume
    
class RAM(ComponentaBase):
    tip=models.CharField(max_length=10)
    capacitate=models.IntegerField()
    frecventa=models.IntegerField()
    latenta=models.CharField(max_length=10)
    nr_module=models.IntegerField()
    def __str__(self):
       return self.Nume
    
class Case(ComponentaBase):
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
        return f"{self.brand} {self.nume} ({self.tip_carcasa})"
    
class Cooler(ComponentaBase):
    tip_racire = models.CharField(max_length=50) # Aer / Lichid (AIO)
    socket_suportate = models.JSONField(default=list)
    inaltime_mm = models.IntegerField(null=True, blank=True) # Pentru cele pe aer
    lungime_radiator_mm = models.IntegerField(null=True, blank=True) # ex: 240, 360

    def __str__(self):
        return f"{self.brand} {self.nume} {self.tip_racire}"