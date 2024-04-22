from django.urls import path
from .views import signup_view, login_view, update_api_key

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    # other paths...
    path('update-api-key/', update_api_key, name='update_api_key'),
]