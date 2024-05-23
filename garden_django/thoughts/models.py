from django.db import models
from pgvector.django import VectorField 
from django.conf import settings


class Garden(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_gardens')
    name = models.CharField(max_length=255)
    visitors = models.ManyToManyField(settings.AUTH_USER_MODEL, through='GardenMembership', related_name='visited_gardens')

    def __str__(self):
        return self.name

class GardenMembership(models.Model):
    garden = models.ForeignKey(Garden, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    can_edit = models.BooleanField(default=False)  # Determines if the user can edit garden content

    class Meta:
        unique_together = ('garden', 'user')

    def __str__(self):
        return f"{self.user}'s role in {self.garden.name}"

class Seed(models.Model):
    garden = models.ForeignKey(Garden, on_delete=models.CASCADE, related_name='seeds')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Content and metadata
    is_youtube = models.BooleanField(default=False)
    content_url = models.URLField(max_length=1024, blank=True, null=True)
    reserve_file = models.FileField(upload_to='reserves/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    transcript = models.TextField(blank=True, null=True)
    
    # Embedding and search
    embedding =  VectorField(dimensions=1536, default = [0]*1536) 
    
    # Metadata
    author = models.CharField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    topics = models.TextField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
class Snippet(models.Model):
    seed = models.ForeignKey(Seed, related_name='parts', on_delete=models.CASCADE)
    content = models.TextField()
    embedding = VectorField(dimensions=1536, default = [0]*1536)
    start_time = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Part of {self.seed.title}"