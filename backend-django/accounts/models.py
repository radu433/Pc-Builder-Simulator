from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    buget_max=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    jocuri_pref=models.JSONField(default=list,blank=True)

    REZOLUTIE_CHOICES = [ ('1080p', 'Full HD (1080p)'), ('1440p', 'Quad HD (1440p)'),('4K', 'Ultra HD (4k)'), ]
    PREFERINTE_CPU = [('Oricare', 'Cel mai ieftin (Default)'),('AMD', 'AMD'), ('Intel', 'Intel'),]

    GPU_CHOICES = [ ('Oricare', 'Cea mai ieftină / Best Value (Default)'), ('NVIDIA', 'NVIDIA (GeForce RTX / GTX)'),
         ('AMD', 'AMD (Radeon RX)'),('Intel', 'Intel (ARC)'),  ]
    PSU_CHOICES = [ ('Oricare', 'Cel mai ieftin (Default)'),
        ('Branduri Recomandate', (
            ('Seasonic', 'Seasonic'),
            ('Corsair', 'Corsair'),
            ('be quiet!', 'be quiet!'),
            ('ASUS', 'ASUS'),
            ('MSI', 'MSI'),
        )),
        ('Alte Branduri', (
            ('EVGA', 'EVGA'),
            ('FSP', 'FSP (Fortron)'),
            ('Gigabyte', 'Gigabyte'),
            ('Thermaltake', 'Thermaltake'),
            ('Deepcool', 'Deepcool'),
        )),
    ]

    rezolutie_dorita = models.CharField(max_length=10, choices=REZOLUTIE_CHOICES, default='1080p')
    locatie=models.CharField(max_length=100, default='Romania')

    gpu_preferat = models.CharField(max_length=20, choices=GPU_CHOICES, default='Oricare', verbose_name="Cip Grafic (GPU) Preferat")
    cpu_preferat = models.CharField(max_length=20, choices=PREFERINTE_CPU, default='Oricare', verbose_name="Procesor (CPU) Preferat")
    psu_preferat = models.CharField(max_length=50, choices=PSU_CHOICES, default='Oricare', verbose_name="Sursă (PSU) Preferată")

    REZOLUTIE_CHOICES = [('1080p', 'Full HD (1080p)'), ('1440p', 'Quad HD (1440p)'),('4K', 'Ultra HD (4k)'), ]
    rezolutie_dorita=models.CharField(max_length=10,choices=REZOLUTIE_CHOICES,default='1080p')

    def __str__(self):
        return f"Profil:{self.user.username}"
    
    def get_cuvinte_cheie_gpu(self):
        
        cuvinte_cheie_gpu = {
            'NVIDIA': ['nvidia', 'geforce', 'rtx', 'gtx'],
            'AMD': ['amd', 'radeon', 'rx'],
            'Intel': ['intel', 'arc']
        }
        
        if self.gpu_preferat in cuvinte_cheie_gpu:
            return cuvinte_cheie_gpu[self.gpu_preferat]
        
        return []
