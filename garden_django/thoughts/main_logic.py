from .models import Seed, Snippet
from .LLM import get_embedding, get_tags
from pytube import YouTube
import json
import requests
from django.core.files.base import ContentFile
from django.conf import settings

def create_seed_from(title: str, context: str = None):
    try:
        # Replace single quotes with double quotes and attempt to load JSON
        llm_tags_str = get_tags(context).replace("'", "\"")
        print(llm_tags_str)
        llm_tags = json.loads(llm_tags_str)
    except json.JSONDecodeError as e:
        # Handle JSON errors specifically
        print(f"Error decoding JSON: {e}")
        llm_tags = {}  # Use an empty dictionary if JSON loading fails
    except Exception as e:
        # Handle any other unforeseen exceptions
        print(f"Unexpected error: {e}")
        llm_tags = {}  # Fallback to an empty dictionary to allow creation of a basic Seed

    try:
        # Create the Seed object, handling missing or malformed fields gracefully
        seed = Seed.objects.create(
            title=title,
            description=llm_tags.get('Description', ""),
            content_url=llm_tags.get('Content URL', ""),
            thumbnail=llm_tags.get('Thumbnail', ""),
            transcript=llm_tags.get('Transcript', ""),
            author=llm_tags.get('Author', ""),
            language=llm_tags.get('Language', ""),
            topics=llm_tags.get('Topics', ""),
            tags=llm_tags.get('Tags', ""),
            year=int(llm_tags.get('Year', '0').strip()) if llm_tags.get('Year', '').strip().isdigit() else None,
        )
        return seed
    except IntegrityError as e:
        # Handle database errors, such as uniqueness constraints being violated
        print(f"Database error during seed creation: {e}")
        return None
    except Exception as e:
        # Catch any other exception that might occur during the creation of the seed
        print(f"Unexpected error during seed creation: {e}")
        return None


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