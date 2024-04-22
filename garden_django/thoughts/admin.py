from django.contrib import admin
from .models import Seed, Snippet, Garden

# Register your models here.
admin.site.register(Seed)
admin.site.register(Snippet)
admin.site.register(Garden)