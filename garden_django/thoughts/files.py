import fitz  # PyMuPDF
from django_q.tasks import async_task

from .main_logic import create_seed_from

from docx import Document
from pytube import YouTube, extract
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

import requests
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import re



def split_text_into_chunks(text, max_chunk_size=600):
    """Splits text into chunks not exceeding max_chunk_size, first by paragraphs, then by sentences, and finally by new lines if needed."""
    chunks = []
    current_chunk = ""

    # Split text by paragraphs first
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        # Further split each paragraph by sentence-ending punctuation
        sentences = re.split(r'(?<=[.?!])\s', paragraph)
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > max_chunk_size:
                if current_chunk:  # Ensure not to append empty strings
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
            else:
                current_chunk += sentence + " "
    
        # Add a newline at the end of each paragraph if it's not empty
        if current_chunk and not current_chunk.endswith('\n'):
            current_chunk += '\n'
    
    # Check if the last accumulated chunk needs to be added
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

def process_and_create_embeddings(text, seed_title, user):
    chunks = split_text_into_chunks(text, max_chunk_size=user.max_chunk_size_setting)

    if chunks:
        first_page_text = chunks[0]
    else:
        first_page_text = ""
        
    seed = create_seed_from(seed_title, first_page_text, user)

    if seed:
        for chunk in chunks:
            # Queue a Django Q task for each chunk
            async_task('thoughts.main_logic.create_snippet_from', chunk, seed, user, group=str(seed.pk))

    return seed

def extract_text_from_pdf(pdf_file):
    """Extracts text from a PDF file."""
    text = ""
    try:
        doc = fitz.open("pdf", pdf_file.read())  # Open the file from memory
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print(f"Failed to extract text from PDF: {e}")
        text = None
    return text

#DOCX
def extract_text_from_docx(docx_path):
    """Extracts text from a DOCX file."""
    doc = Document(docx_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


#Youtube

def extract_text_from_youtube(youtube_url):
    """Extracts text from a YouTube captions file using youtube-transcript-api."""
    video_id = extract.video_id(youtube_url)  # Simple extraction of video ID from URL
    try:
        # Attempt to fetch the transcript list of the video
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get English transcript or fallback to any available transcript
        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            # Fallback to the first available transcript if English is not available
            transcripts = list(transcript_list)
            if transcripts:
                transcript = transcripts[0]  # Select the first available transcript
            else:
                return "No transcripts available."

        # Format the transcript as SRT
        formatter = TextFormatter()
        srt = formatter.format_transcript(transcript.fetch())
        return srt
    except Exception as e:
        return f"An error occurred: {str(e)}"
    

def download_and_save_video_to_seed(youtube_url, seed):
    """Downloads a YouTube video and updates the corresponding Seed model instance."""
    try:
        # Create a YouTube object
        yt = YouTube(youtube_url)
        
        # Get the highest resolution progressive stream URL
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4')\
                                  .order_by('resolution').desc().first()
        
        if not video_stream:
            raise ValueError("No suitable video stream found.")
        
        # Use requests to fetch the video content
        response = requests.get(video_stream.url, stream=True)
        
        if response.status_code != 200:
            raise IOError("Failed to download video")
        
        # Create a unique filename for the video
        filename = f"youtube/{yt.title.replace(' ', '_').replace('/', '_')}.mp4"
        
        # Save the video file to Django's default storage
        video_content = ContentFile(response.content)  
        file_path = default_storage.save(filename, video_content)
        
        # Update the Seed model instance
        seed.reserve_file = file_path  
        seed.save()
        
        return "Video downloaded and saved successfully."
    except Exception as e:
        return f"Error processing YouTube URL: {str(e)}"