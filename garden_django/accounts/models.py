from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class CustomUser(AbstractUser):
    api_key = models.CharField(max_length=255, blank=True, null=True)
    use_system_api_key = models.BooleanField(default=False)
    max_chunk_size_setting = models.IntegerField(default=600)