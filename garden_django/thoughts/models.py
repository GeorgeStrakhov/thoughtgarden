from django.db import models
from pgvector.django import VectorField 


# Create your models here.
class Seed(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Content and metadata
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

    def __str__(self):
        return f"Part of {self.seed.title}"