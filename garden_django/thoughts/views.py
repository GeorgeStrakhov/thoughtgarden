from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .forms import SeedForm, SearchForm, FileUploadForm, YouTubeForm
from .models import Seed, Snippet
from .main_logic import create_seed_from_youtube, create_seed_from
from .LLM import get_embedding
from .files import extract_text_from_youtube

from django.core.paginator import Paginator

from django.core.files.storage import default_storage, FileSystemStorage

from django.db.models import F
from pgvector.django import L2Distance
from .files import extract_text_from_pdf, extract_text_from_docx, process_and_create_embeddings, \
    split_text_into_chunks
from django_q.tasks import async_task


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

def seeds_list(request):
    seeds = Seed.objects.all()  # Fetch all seeds from the database
    return render(request, 'thoughts/seeds_list.html', {'seeds': seeds})


def create_seed(request):
    if request.method == 'POST':
        form = SeedForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            content = form.cleaned_data['content']
            seed = create_seed_from(title, content)

            # Break down the caption text into chunks and process asynchronously.
            for chunk in split_text_into_chunks(content):
                async_task('thoughts.main_logic.create_snippet_from', chunk, seed)

            return redirect('seed_detail_view', pk=seed.pk)
    else:
        form = SeedForm()
    return render(request, 'thoughts/create_seed.html', {'form': form})


def search_seeds(request):
    form = SearchForm()
    parts = None  
    search_text = ""

    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['search_text']
            search_text = form.cleaned_data['search_text']
            embedding = get_embedding(text)
            parts = Snippet.objects.annotate(
                distance=L2Distance(F('embedding'), embedding)
            ).order_by('distance')[:5]

    return render(request, 'thoughts/search_and_display.html', {
        'form': form,
        'parts': parts,
        'search_text': search_text,  
    })

def find_similar_seeds(request, snippet_id):
    # Fetch the Idea Part based on the given ID
    target_part = get_object_or_404(Snippet, pk=snippet_id)
    target_embedding = target_part.embedding  # Assuming the embedding is stored in the 'embedding' field
    
    similar_parts = Snippet.objects.annotate(
        distance=L2Distance(F('embedding'), target_embedding)
    ).exclude(id=snippet_id).order_by('distance')[:6]
    
    return render(request, 'thoughts/similar_seeds.html', {
        'similar_parts': similar_parts,
        'target_part': target_part,
    })

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
            seed = create_seed_from_youtube(youtube_url, caption_text)

            # Download video to default storage if 'download_video' is checked.
            if download_video:
                async_task('thoughts.files.download_and_save_video_to_seed', youtube_url, seed)

            # Break down the caption text into chunks and process asynchronously.
            for chunk in split_text_into_chunks(caption_text):
                async_task('thoughts.main_logic.create_snippet_from', chunk, seed)
            # Optional: Further processing with caption_text or idea.
        except Exception as e:
            return HttpResponse(f"Error processing YouTube URL: {str(e)}", status=500)
        
        return redirect('seed_detail_view', pk=seed.pk) 
    else:
        return HttpResponse("Invalid request method.", status=405)


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
            seed = process_and_create_embeddings(text, seed_title)

            if upload_to_s3:
                default_storage.save(uploaded_file.name, uploaded_file)

            return redirect('seed_detail_view', pk=seed.pk) 

    else:
        form = FileUploadForm()
    return render(request, 'thoughts/upload_file.html', {'form': form})

def seed_detail_view(request, pk):
    seed = get_object_or_404(Seed, pk=pk)
    parts_list = seed.parts.all().order_by('id') 
    paginator = Paginator(parts_list, 10)
    page_number = request.GET.get('page')
    parts = paginator.get_page(page_number)

    highlighted_part_id = request.GET.get('highlight')
    highlighted_part = None

    if highlighted_part_id:
        try:
            highlighted_part = Snippet.objects.get(id=highlighted_part_id, seed=seed)
        except Snippet.DoesNotExist:
            highlighted_part = None

    return render(request, 'thoughts/seed_detail.html', {
        'seed': seed,
        'parts': parts,
        'highlighted_part': highlighted_part,
    })