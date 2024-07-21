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

from django.utils.text import slugify
import datetime
import uuid
import logging

logger = logging.getLogger(__name__)



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

#PDF
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


#YOUTUBE

def format_transcript(transcript, pause_threshold=2.0, max_sentences=10, max_words=300):
    '''
    Helper function to reformat transcript to paragraph-by-paragraph versus very short snippets that the API returns by default.
    '''

    paragraphs = []
    paragraphs_text = ""
    current_paragraph = []
    current_word_count = 0
    current_sentence_count = 0
    start_time_of_current_paragraph = None

    for i, entry in enumerate(transcript):
        current_word_count += len(entry['text'].split())
        current_sentence_count += entry['text'].count('.')

        # Store the start time of the current paragraph
        if start_time_of_current_paragraph is None:
            start_time_of_current_paragraph = entry.get('start', 0)

        current_paragraph.append(entry['text'])

        # Check if the current entry is the last one
        is_last = i == len(transcript) - 1

        # If it's not the last entry, calculate the pause before the next entry
        if not is_last:
            next_entry = transcript[i + 1]
            pause = next_entry['start'] - (entry['start'] + entry['duration'])
        else:
            pause = None

        # Check conditions to end the paragraph
        should_break = (
            is_last or
            (pause and pause > pause_threshold) or
            current_word_count >= max_words or
            current_sentence_count >= max_sentences
        )

        if should_break:
            paragraph_text = ' '.join(current_paragraph)
            # Ensure the start time is not negative
            rounded_start_time = max(0, int(round(start_time_of_current_paragraph)))
            paragraphs.append({
                'text': paragraph_text,
                'start_time': rounded_start_time
            })
            paragraphs_text += paragraph_text + '\n\n'

            # Reset counters and lists
            current_paragraph = []
            current_word_count = 0
            current_sentence_count = 0
            start_time_of_current_paragraph = None
    return paragraphs, paragraphs_text



def extract_text_from_youtube(youtube_url, video_id=None):
    """Extracts text from a YouTube captions file using youtube-transcript-api."""
    logging.debug("Starting extract_text_from_youtube with video_id: %s", video_id)
    
    if video_id is None:
        video_id = extract.video_id(youtube_url)  # Simple extraction of video ID from URL
        logging.debug("Extracted video_id: %s", video_id)
    
    try:
        # Attempt to fetch the transcript list of the video
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        logging.debug("Transcript list obtained: %s", transcript_list)

        # Try to get English transcript or fallback to any available transcript
        try:
            transcript = transcript_list.find_transcript(['en'])
            logging.debug("English transcript found")
        except Exception as e:
            logging.debug("English transcript not found: %s", str(e))
            # Fallback to the first available transcript if English is not available
            transcripts = list(transcript_list)
            if transcripts:
                transcript = transcripts[0]  # Select the first available transcript
                logging.debug("Using first available transcript")
            else:
                logging.error("No transcripts available")
                return "No transcripts available."

        you_list, you_text = format_transcript(transcript.fetch())
        logging.debug("Formatted captions: %s", you_list)
        logging.debug("Formatted text: %s", you_text)
        return you_list, you_text
    except Exception as e:
        logging.error("An error occurred: %s", str(e))
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
    
        
        # Save the video file to Django's default storage
        username = seed.garden.owner.username

        # Create a sanitized and unique filename for the video
        safe_title = slugify(yt.title)[:50] 
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        unique_suffix = uuid.uuid4().hex[:8]  # Ensures uniqueness
        filename = f"{username}/youtube/{safe_title}_{timestamp}_{unique_suffix}.mp4"

        try:
            video_content = ContentFile(response.content)
            file_path = default_storage.save(filename, video_content)
            
            # Update the Seed model instance
            seed.reserve_file = file_path  
            seed.save()
        except Exception as e:
            # Log the error or handle it appropriately
            logger.error(f"Failed to save video for seed {seed.id}: {str(e)}")
            # Optionally, re-raise the error or handle it as per your application's requirements
            raise        # Save the video file to Django's default storage

        
        return "Video downloaded and saved successfully."
    except Exception as e:
        return f"Error processing YouTube URL: {str(e)}"