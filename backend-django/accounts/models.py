from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    buget_max=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    jocuri_pref=models.JSONField(default=list,blank=True)
    locatie=models.CharField(max_length=100, default='Romania')

    REZOLUTIE_CHOICES = [('1080p', 'Full HD (1080p)'), ('1440p', 'Quad HD (1440p)'),('4K', 'Ultra HD (4k)'), ]
    rezolutie_dorita=models.CharField(max_length=10,choices=REZOLUTIE_CHOICES,default='1080p')

    def __str__(self):
        return f"Profil:{self.user.username}"
