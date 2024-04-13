from .models import Seed, Snippet
from .LLM import get_embedding, get_tags
from pytube import YouTube
import json
import requests
from django.core.files.base import ContentFile
from django.conf import settings

def create_seed_from(title : str, context: str = None):
    llm_tags_str = get_tags(context).replace("'", "\"")
    llm_tags = json.loads(llm_tags_str)
    seed = Seed.objects.create(
        title=title,
        description=llm_tags.get('Description', None),
        content_url=llm_tags.get('Content URL', None),
        thumbnail=llm_tags.get('Thumbnail', None),
        transcript=llm_tags.get('Transcript', None),
        author=llm_tags.get('Author', None),
        language=llm_tags.get('Language', None),
        topics=llm_tags.get('Topics', None),
        tags=llm_tags.get('Tags', None),
        year = int(llm_tags.get('Year')) if llm_tags.get('Year', '0').strip() else None,
        # Assuming embedding needs to be handled separately as it requires a specific format
        # embedding=process_embedding(llm_tags.get('Embedding', None)),
    )
    return seed


def save_thumbnail(url, title):
    """Fetches a thumbnail from a URL and returns a ContentFile."""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        # Assuming the thumbnail is a JPEG image
        thumbnail_content = ContentFile(response.content)
        filename = f"{title}_thumbnail.jpg"  # You might want to sanitize or hash the title
        return filename, thumbnail_content
    return None, None

def create_seed_from_youtube(url, video_text):
    yt = YouTube(url)
    
    #Somehow this fix tags
    stream = yt.streams.first()

    thumbnail_filename, thumbnail_content = save_thumbnail(yt.thumbnail_url, yt.title)
    
    seed = Seed(
        title=yt.title,
        description=yt.description,
        content_url=url,
        author=yt.author,
        transcript=video_text,
        tags=", ".join(yt.keywords),
        year=yt.publish_date.year if yt.publish_date else None,
    )
    
    if thumbnail_content:
        seed.thumbnail.save(thumbnail_filename, thumbnail_content, save=True)
    
    seed.save()  # Save the idea after setting all fields
    
    return seed


def create_snippet_from(text: str, seed: Seed):
    embedding = get_embedding(text)
    snippet = Snippet.objects.create(content=text, seed=seed, embedding=embedding)
    return snippet