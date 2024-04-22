from django.db.models import QuerySet
from .models import Garden, Snippet, Seed
from django.db.models import Q

def get_accessible_gardens(user):
    """Retrieve all gardens accessible to the given user."""
    # Combine queries using Q objects for any of the conditions being true
    accessible_gardens = Garden.objects.filter(
        Q(owner=user) | 
        Q(gardenmembership__user=user)
    ).distinct()

    return accessible_gardens

def filter_snippets_for_user(user) -> QuerySet:
    """Retrieve snippets from seeds that are in gardens accessible to the user."""
    accessible_gardens = get_accessible_gardens(user)
    return Snippet.objects.filter(seed__garden__in=accessible_gardens)

def filter_seeds_for_user(user) -> QuerySet:
    """Retrieve seeds from gardens accessible to the user."""
    accessible_gardens = get_accessible_gardens(user)
    return Seed.objects.filter(garden__in=accessible_gardens)