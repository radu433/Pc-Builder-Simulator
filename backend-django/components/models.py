from django.db import models
from django.contrib.auth.models import User

class ComponentaBase(models.Model):
    nume = models.CharField(max_length=300)
    brand = models.CharField(max_length=200)
    pret = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    magazin = models.CharField(max_length=100, null=True, blank=True)
    url_produs = models.URLField(max_length=500, null=True, blank=True)
    part_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
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
    tip_vram = models.CharField(max_length=50, null=True, blank=True)
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
    threaduri = models.IntegerField(null=True, blank=True)
    frecventa_ghz = models.DecimalField(max_digits=4, decimal_places=2)
    consum_tdp = models.IntegerField()

    def __str__(self):
        return self.nume

class Motherboard(ComponentaBase):
    socket = models.CharField(max_length=100)
    chipset = models.CharField(max_length=100)
    format = models.CharField(max_length=50)
    tip_memorie = models.CharField(max_length=50)
    sloturi_ram = models.IntegerField(default=4) 
    nr_sloturi_m2 = models.IntegerField(default=1)
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
    lungime_max_gpu_mm = models.IntegerField(null=True, blank=True) 
    inaltime_max_cooler_mm = models.IntegerField(null=True, blank=True)
    suport_radiator_mm = models.JSONField(default=list)
    
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

class Storage(ComponentaBase):
    TIP_STORAGE_CHOICES = [
        ('SSD', 'Solid State Drive'),
        ('HDD', 'Hard Disk Drive'),
        ('NVME', 'M.2 NVMe'),
    ]
    tip = models.CharField(max_length=10, choices=TIP_STORAGE_CHOICES)
    capacitate_gb = models.IntegerField()
    interfata = models.CharField(max_length=100) # ex: SATA III, PCIe 5.0 x4
    viteza_citire_mb_s = models.IntegerField(null=True, blank=True)
    viteza_scriere_mb_s = models.IntegerField(null=True, blank=True)
    format = models.CharField(max_length=50) # ex: 2.5", M.2 2280, 3.5"

    def __str__(self):
        return f"{self.nume} ({self.capacitate_gb}GB)"

class Monitor(ComponentaBase):
    diagonala_inch = models.DecimalField(max_digits=4, decimal_places=1)
    rezolutie = models.CharField(max_length=50) # ex: 2560x1440
    rata_refresh_hz = models.IntegerField()
    tip_panou = models.CharField(max_length=50) # ex: IPS, OLED, VA
    timp_raspuns_ms = models.DecimalField(max_digits=3, decimal_places=1)
    aspect_ratio = models.CharField(max_length=20, default="16:9")
    are_boxe = models.BooleanField(default=False)

class Fan(ComponentaBase):
    dimensiune_mm = models.IntegerField() # ex: 120, 140
    tip_conector = models.CharField(max_length=50) # ex: 4-pin PWM, 3-pin
    flux_aer_cfm = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_zgomot_db = models.DecimalField(max_digits=4, decimal_places=1)
    are_rgb = models.BooleanField(default=False)


class NetworkAdapter(ComponentaBase):
    interfata = models.CharField(max_length=100) # ex: PCIe x1, USB 3.0
    viteza_maxima_mbps = models.IntegerField()
    standard_wireless = models.CharField(max_length=100, null=True, blank=True) # ex: Wi-Fi 7, Wi-Fi 6E
    are_bluetooth = models.BooleanField(default=False)


class SaveBuild(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='builds') #leg de utilizator
    nume = models.CharField(max_length=100, blank=True)

    cpu = models.ForeignKey(CPU, on_delete=models.SET_NULL, null=True, blank=True)
    gpu = models.ForeignKey(GPU, on_delete=models.SET_NULL, null=True, blank=True)
    motherboard = models.ForeignKey(Motherboard, on_delete=models.SET_NULL, null=True, blank=True)
    ram = models.ForeignKey(RAM, on_delete=models.SET_NULL, null=True, blank=True)
    storage = models.ForeignKey(Storage, on_delete=models.SET_NULL, null=True, blank=True)
    psu = models.ForeignKey(PSU, on_delete=models.SET_NULL, null=True, blank=True)
    case = models.ForeignKey(Case, on_delete=models.SET_NULL, null=True, blank=True)
    cooler = models.ForeignKey(Cooler, on_delete=models.SET_NULL, null=True, blank=True)
        
    pret_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    data_salvarii = models.DateTimeField(auto_now_add=True)  

def save(self, *args, **kwargs):
       
        if not self.nume:
            #numaram al catelea pc salvat este 
            numar_pc_uri_existente = SaveBuild.objects.filter(user=self.user).count()
            # Setăm numele adăugând +1 la numărătoare
            self.nume = f"My Custom PC {numar_pc_uri_existente + 1}"
            
        #functia de salvare in baza de date
        super().save(*args, **kwargs)

def __str__(self):
    return f"{self.nume} - {self.user.username}"