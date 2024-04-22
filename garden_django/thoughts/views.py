from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .forms import SeedForm, SearchForm, FileUploadForm, YouTubeForm, SeedBigForm
from .models import Seed, Snippet, Garden
from .main_logic import create_seed_from_youtube, create_seed_from
from .LLM import get_embedding
from .files import extract_text_from_youtube

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

from django.core.files.storage import default_storage, FileSystemStorage

from django.db.models import F
from pgvector.django import L2Distance
from .files import extract_text_from_pdf, extract_text_from_docx, process_and_create_embeddings, \
    split_text_into_chunks
from django_q.tasks import async_task
from django_q.models import Task

import datetime
import uuid
from django.utils.text import slugify
import logging

from .db_walker import filter_snippets_for_user, filter_seeds_for_user

logger = logging.getLogger(__name__)

@login_required
def submit_content(request):
    # Initialize forms for text, YouTube URL, and file upload
    text_form = SeedForm()
    youtube_form = YouTubeForm()
    file_upload_form = FileUploadForm()

    # Render the template with all forms
    return render(request, 'thoughts/seed_upload.html', {
        'text_form': text_form,
        'youtube_form': youtube_form,
        'file_upload_form': file_upload_form
    })


@login_required
def seeds_list(request):
    if not request.user.owned_gardens.exists():
        #TODO: Create a default garden for the user
        Garden.objects.create(owner=request.user, name=f"{request.user.username}'s Garden")

    seeds = filter_seeds_for_user(request.user)
    return render(request, 'thoughts/seeds_list.html', {'seeds': seeds})


@login_required
def create_seed(request):
    if request.method == 'POST':
        form = SeedForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            content = form.cleaned_data['content']
            seed = create_seed_from(title, content, request.user)

            # Break down the caption text into chunks and process asynchronously.
            if seed:
                for chunk in split_text_into_chunks(content, max_chunk_size=request.user.max_chunk_size_setting):
                    async_task('thoughts.main_logic.create_snippet_from', chunk, seed, request.user, group=str(seed.pk))

            return redirect('seed_detail_view', pk=seed.pk)
    else:
        form = SeedForm()
    return render(request, 'thoughts/create_seed.html', {'form': form})

@login_required
def search_seeds(request):
    form = SearchForm()
    parts = None  
    search_text = ""

    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            search_text = form.cleaned_data['search_text']
            embedding = get_embedding(search_text, request.user)

            # Now filter Snippets whose Seed is in one of the accessible gardens
            parts = filter_snippets_for_user(request.user).annotate(
                distance=L2Distance(F('embedding'), embedding)
            ).order_by('distance')[:15]

    return render(request, 'thoughts/search_and_display.html', {
        'form': form,
        'parts': parts,
        'search_text': search_text,
    })

@login_required
def find_similar_seeds(request, snippet_id):
    # Fetch the Idea Part based on the given ID
    target_part = get_object_or_404(Snippet, pk=snippet_id)
    target_embedding = target_part.embedding  # Assuming the embedding is stored in the 'embedding' field
    
    similar_parts = filter_snippets_for_user(request.user).annotate(
        distance=L2Distance(F('embedding'), target_embedding)
    ).exclude(id=snippet_id).order_by('distance')[:6]
    
    return render(request, 'thoughts/similar_seeds.html', {
        'similar_parts': similar_parts,
        'target_part': target_part,
    })

@login_required
def process_youtube_url(request):
    if request.method == 'POST':
        # Retrieve the URL and whether to download the video from the form.
        form = YouTubeForm(request.POST)
        if form.is_valid():
            youtube_url = form.cleaned_data['url']
            download_video = form.cleaned_data['download']

        if not youtube_url:
            return HttpResponse("No YouTube URL provided.", status=400)
        
        try:
            # Extract captions or relevant text from the YouTube video.
            caption_text = extract_text_from_youtube(youtube_url)
            # Create a new idea or entity in your system based on the YouTube video.
            seed = create_seed_from_youtube(youtube_url, caption_text, request.user)

            # Download video to default storage if 'download_video' is checked.
            if download_video:
                async_task('thoughts.files.download_and_save_video_to_seed', youtube_url, seed, group=str(seed.pk))

            # Break down the caption text into chunks and process asynchronously.
            if seed:
                for chunk in split_text_into_chunks(caption_text, max_chunk_size=request.user.max_chunk_size_setting):
                    async_task('thoughts.main_logic.create_snippet_from', chunk, seed, request.user, group=str(seed.pk))
            # Optional: Further processing with caption_text or idea.
        except Exception as e:
            return HttpResponse(f"Error processing YouTube URL: {str(e)}", status=500)
        
        return redirect('seed_detail_view', pk=seed.pk) 
    else:
        return HttpResponse("Invalid request method.", status=405)

@login_required
def upload_and_process_file_view(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            seed_title = form.cleaned_data.get('title', 'Untitled')
            upload_to_s3 = form.cleaned_data['upload_to_s3']

            # Determine the file type and process accordingly
            if uploaded_file.name.endswith('.pdf'):
                # Process a PDF file
                text = extract_text_from_pdf(uploaded_file)
            elif uploaded_file.name.endswith('.docx'):
                # Process a DOCX file
                text = extract_text_from_docx(uploaded_file)
            else:
                return HttpResponse("Unsupported file type.", status=400)

            # Process the extracted text
            seed = process_and_create_embeddings(text, seed_title, request.user)

            if upload_to_s3:
                username = request.user.username
                safe_filename = slugify(uploaded_file.name.rsplit('.', 1)[0])
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                extension = uploaded_file.name.rsplit('.', 1)[-1] if '.' in uploaded_file.name else ''
                unique_filename = f"{username}/{safe_filename}_{timestamp}_{uuid.uuid4().hex}.{extension}"
                try:
                    saved_path = default_storage.save(unique_filename, uploaded_file)
                    seed.reserve_file = saved_path
                    seed.save()
                except Exception as e:
                    # Log the error
                    logger.error(f"Failed to save file: {e}")
                    return HttpResponse("Error saving file.", status=500)

            return redirect('seed_detail_view', pk=seed.pk) 

    else:
        form = FileUploadForm()
    return render(request, 'thoughts/upload_file.html', {'form': form})

@login_required
def seed_detail_view(request, pk):
    #Look for seed only in the user's gardens
    seed = get_object_or_404(filter_seeds_for_user(request.user), pk=pk)

    parts_list = seed.parts.all().order_by('id')
    paginator = Paginator(parts_list, 10)
    page_number = request.GET.get('page')
    parts = paginator.get_page(page_number)

    highlighted_part_id = request.GET.get('highlight')
    highlighted_part = None
    previous_parts = []
    after_parts = []

    if highlighted_part_id:
        try:
            highlighted_part = Snippet.objects.get(id=highlighted_part_id, seed=seed)
            # Find the index of the highlighted part
            highlighted_index = list(parts_list).index(highlighted_part)
            # Calculate the correct page number based on the index
            correct_page_number = highlighted_index // paginator.per_page + 1
            
            # Adjust the page number to ensure the highlighted part is on the current page
            page_number = correct_page_number
        except (Snippet.DoesNotExist, ValueError):
            # Handle cases where the snippet does not exist or is not in the list
            highlighted_part = None

    # Get the parts for the adjusted or initial page number
    parts = paginator.get_page(page_number)

    return render(request, 'thoughts/seed_detail.html', {
        'seed': seed,
        'parts': parts,
        'highlighted_part': highlighted_part,
        'previous_parts': previous_parts,
        'after_parts': after_parts,
    })

@login_required
def seed_edit_view(request, pk):
    seed_id = pk
    seed = get_object_or_404(Seed, id=seed_id)
    if request.method == 'POST':
        form = SeedBigForm(request.POST, request.FILES, instance=seed)
        if form.is_valid():
            form.save()
            return redirect('seed_detail_view', pk=seed.id)  # Assuming you have a detail view for Seed
    else:
        form = SeedBigForm(instance=seed)
    return render(request, 'thoughts/seed_edit.html', {'form': form, 'seed': seed})


@login_required
def home(request):
    return redirect('seeds_list')  # Redirect to the seeds list view