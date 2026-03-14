from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('Member', 'Member'),
        # Add other roles later if needed
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Member')
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)

    def __str__(self):
        return self.username