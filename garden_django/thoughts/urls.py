from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.seeds_list, name='seeds_list'),
    path("home/", views.home, name='home'),
    path('create/', views.submit_content, name='submit_content'),
    path('search/', views.search_seeds, name='search_seeds'),
    
    path('seeds/<int:pk>/', views.seed_detail_view, name='seed_detail_view'),
    path('seeds/<int:pk>/edit/', views.seed_edit_view, name='seed_edit_view'),

    path('seeds/similar/<int:snippet_id>/', views.find_similar_seeds, name='find_similar_seeds'),

    #Process forms ednpoints
    path('upload_file/', views.upload_and_process_file_view, name='upload_file'),
    path('process_youtube_url/', views.process_youtube_url, name='process_youtube_url'),
    path('create_seed/', views.create_seed, name='create_seed'),

    
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)