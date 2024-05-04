import os
import django

# Initialize Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "garden.settings")
django.setup()

from django.contrib.auth import get_user_model

# Get the custom user model
CustomUser = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "adminpassword")

if not CustomUser.objects.filter(username=username).exists():
    CustomUser.objects.create_superuser(username, email, password, use_system_api_key = True)
    print(f"Superuser {username} created.")
else:
    print(f"Superuser {username} already exists.")
