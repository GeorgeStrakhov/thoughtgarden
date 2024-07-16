# telegram_bot/bot.py
import logging
import os
import uuid
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage, FileSystemStorage
from django.core.paginator import Paginator
from django.db import IntegrityError, models
from django.db.models import F
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify

from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext

from django_q.tasks import async_task
from django_q.models import Task
from pgvector.django import L2Distance

from thoughts.db_walker import filter_snippets_for_user, filter_seeds_for_user
from thoughts.files import (extract_text_from_pdf, extract_text_from_docx, process_and_create_embeddings,
                    split_text_into_chunks, extract_text_from_youtube)
from thoughts.main_logic import create_seed_from_youtube, create_seed_from
from thoughts.models import Seed, Snippet, Garden
from thoughts.LLM import get_embedding, get_user_intent

from asgiref.sync import sync_to_async



# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve bot token from environment variable
TOKEN_TG = settings.TOKEN_TG

if TOKEN_TG is None:
    raise ValueError("No Telegram bot token provided. Please set the TELEGRAM_BOT_TOKEN environment variable.")

# States for the conversation handler
ASK_API_KEY, ASK_PASSWORD, AUTHENTICATED = range(3)

User = get_user_model()

@sync_to_async
def get_user_by_telegram_id(telegram_id):
    return User.objects.get(telegram_id=telegram_id)

@sync_to_async
def get_or_create_user(telegram_id, username, email):
    return User.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={'username': username, 'email': email}
    )

@sync_to_async
def save_user(user):
    user.save()

@sync_to_async
def filter_seeds_for_user(custom_user):
    return Seed.objects.filter(garden__owner=custom_user)

@sync_to_async
def filter_snippets_for_user(custom_user):
    return Snippet.objects.filter(seed__garden__owner=custom_user)

@sync_to_async
def get_seed(seed_id, custom_user):
    return Seed.objects.get(id=seed_id, garden__owner=custom_user)

@sync_to_async
def get_snippet(snippet_id, custom_user):
    return Snippet.objects.get(id=snippet_id, seed__garden__owner=custom_user)

def start(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    telegram_id = user.id
    
    try:
        custom_user = User.objects.get(telegram_id=telegram_id)
        update.message.reply_text('Welcome back! You are already authenticated.')
        return AUTHENTICATED
    except User.DoesNotExist:
        update.message.reply_text(
            'Welcome! Please send your OpenAI API key or type "password" to use a system-wide key.',
            reply_markup=ForceReply(selective=True),
        )
        return ASK_API_KEY

def handle_api_key(update: Update, context: CallbackContext) -> int:
    api_key = update.message.text
    user = update.message.from_user
    telegram_id = user.id
    custom_user, created = User.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={'username': f'tg_{telegram_id}', 'email': f'{telegram_id}@example.com'}
    )
    if created:
        custom_user.set_unusable_password()
    
    if api_key.lower() == 'password':
        update.message.reply_text('Please enter the system password:')
        return ASK_PASSWORD
    else:
        custom_user.api_key = api_key
        custom_user.save()
        update.message.reply_text('API key saved. You are now authenticated.')
        return AUTHENTICATED

def handle_password(update: Update, context: CallbackContext) -> int:
    password = update.message.text
    user = update.message.from_user
    telegram_id = user.id
    custom_user = User.objects.get(telegram_id=telegram_id)
    
    if password == settings.SYSTEM_PASSWORD:
        custom_user.use_system_api_key = True
        custom_user.save()
        update.message.reply_text('Password correct. You are now authenticated using the system API key.')
        return AUTHENTICATED
    else:
        update.message.reply_text('Incorrect password. Please try again.')
        return ASK_PASSWORD

def authenticated(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    telegram_id = user.id
    custom_user = User.objects.get(telegram_id=telegram_id)
    if not user.owned_gardens.exists():
        #TODO: Create a default garden for the user
        Garden.objects.create(owner=custom_user, name=f"{custom_user.username}'s Garden")

    update.message.reply_text("You are authenticated. Use /plant to plant a seed or /search to find similarities.")

def list_seeds(update: Update, context: CallbackContext) -> None:
    # Logic to list seeds
    user = update.message.from_user
    telegram_id = user.id
    custom_user = User.objects.get(telegram_id=telegram_id)
    seeds = filter_seeds_for_user(custom_user)
    seeds_list = "\n".join([f"{seed.id}: {seed.title}" for seed in seeds])
    update.message.reply_text(f"Here are your seeds:\n{seeds_list}")

def create_seed(update: Update, context: CallbackContext) -> None:
    message_parts = update.message.text.split()
    if len(message_parts) < 3:
        update.message.reply_text("Please provide a title and content after /create_seed_from_message command.")
        return

    title, content = message_parts[1], ' '.join(message_parts[2:])

    user = update.message.from_user
    telegram_id = user.id
    custom_user = User.objects.get(telegram_id=telegram_id)

    try:
        seed = create_seed_from(title, content, custom_user)

        # Break down the content into chunks and process asynchronously.
        for chunk in split_text_into_chunks(content, max_chunk_size=custom_user.max_chunk_size_setting):
            async_task('thoughts.main_logic.create_snippet_from', chunk, seed, custom_user, group=str(seed.pk))

        update.message.reply_text(f"Seed created with ID: {seed.pk}")

    except Exception as e:
        update.message.reply_text(f"Error while creating seed from message: {str(e)}")


def search(update: Update, context: CallbackContext) -> None:
    search_text = update.message.text[len("/search_seeds "):] 

    if not search_text.strip():
        update.message.reply_text("Please provide a search query after the /search_seeds command.")
        return

    user = update.message.from_user
    telegram_id = user.id
    custom_user = User.objects.get(telegram_id=telegram_id)

    try:
        embedding = get_embedding(search_text, custom_user)

        parts = filter_snippets_for_user(custom_user).annotate(
            distance=L2Distance(F('embedding'), embedding)
        ).order_by('distance')[:15]

        # Format search results as a text message
        message = f"**Search Results for:** {search_text}\n"
        for part in parts:
            message += f"{part.id}: {part.content}\n\n"

        update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        update.message.reply_text(f"Error while searching seeds: {str(e)}")

def find_similar(update: Update, context: CallbackContext) -> None:
    snippet_id = update.message.text.split()[-1]  # Assuming the snippet ID is provided as the last word in the message
    try:
        snippet_id = int(snippet_id)
    except ValueError:
        update.message.reply_text("Invalid snippet ID. Please provide a valid snippet ID.")
        return

    user = update.message.from_user
    telegram_id = user.id
    custom_user = User.objects.get(telegram_id=telegram_id)
    
    try:
        target_part = Snippet.objects.get(id=snippet_id, seed__garden__owner=custom_user)
        target_embedding = target_part.embedding

        similar_parts = filter_snippets_for_user(custom_user).annotate(
            distance=L2Distance(F('embedding'), target_embedding)
        ).exclude(id=snippet_id).order_by('distance')[:6]

        # Format search results as a text message
        message = f"**Similar Seeds for Snippet** (ID: {snippet_id})\n"
        for part in similar_parts:
            message += f"{part.id}: {part.content}\n\n"

        update.message.reply_text(message, parse_mode='Markdown')
    except Snippet.DoesNotExist:
        update.message.reply_text("No snippet found with the provided ID.")

def process_youtube(update: Update, context: CallbackContext) -> None:

    user = update.message.from_user
    telegram_id = user.id
    custom_user = User.objects.get(telegram_id=telegram_id)

    # Process YouTube URL sent in message
    youtube_url = update.message.text
    
    if not youtube_url:
        update.message.reply_text("No YouTube URL provided.")
        return
    
    try:
        # Extract captions or relevant text from the YouTube video.
        caption_text_list, caption_text = extract_text_from_youtube(youtube_url)
        
        # Create a new seed in your system based on the YouTube video.
        seed = create_seed_from_youtube(youtube_url, caption_text, custom_user)
        
        # Download video to default storage if needed (not implemented in this bot)
        # TODO Download all videos?
        async_task('thoughts.files.download_and_save_video_to_seed', youtube_url, seed, group=str(seed.pk))
        
        # Process each chunk of caption text asynchronously
        for chunk in caption_text_list:
            chunk_text = chunk.get('text', '')
            async_task('thoughts.main_logic.create_snippet_from', chunk_text, seed, custom_user, group=str(seed.pk))
        
        update.message.reply_text(f"YouTube video processed. Seed ID: {seed.pk}")

    except Exception as e:
        update.message.reply_text(f"Error processing YouTube URL: {str(e)}")

def upload_file(update: Update, context: CallbackContext) -> None:
    # Process uploaded file sent in message
    uploaded_file = update.message.document
    
    if not uploaded_file:
        update.message.reply_text("No file uploaded.")
        return
    
    try:
        # Determine file type and process
        if uploaded_file.file_name.endswith('.pdf'):
            text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.file_name.endswith('.docx'):
            text = extract_text_from_docx(uploaded_file)
        else:
            update.message.reply_text("Unsupported file type.")
            return
        
        # Process the extracted text to create a seed
        seed_title = uploaded_file.file_name.rsplit('.', 1)[0]
        user = User.objects.get(telegram_id=update.message.from_user.id)
        seed = process_and_create_embeddings(text, seed_title, user)
        
        update.message.reply_text(f"File uploaded and processed. Seed ID: {seed.pk}")

    except Exception as e:
        update.message.reply_text(f"Error processing uploaded file: {str(e)}")

def seed_detail(update: Update, context: CallbackContext) -> None:
    seed_id = update.message.text.split()[-1]  # Assuming the seed ID is provided as the last word in the message
    try:
        seed_id = int(seed_id)
    except ValueError:
        update.message.reply_text("Invalid seed ID. Please provide a valid seed ID.")
        return

    user = update.message.from_user
    telegram_id = user.id
    custom_user = User.objects.get(telegram_id=telegram_id)
    
    try:
        seed = Seed.objects.get(id=seed_id, garden__owner=custom_user)  # Ensure the seed belongs to the user
        snippets = seed.snippet_set.all().order_by('id')

        # Format seed and snippets as a text message
        message = f"**Seed** (ID: {seed.id})\nTitle: {seed.title}\n\n**Snippets:**\n"
        for snippet in snippets:
            message += f"{snippet.id}: {snippet.content}\n\n"
        
        update.message.reply_text(message, parse_mode='Markdown')
    except Seed.DoesNotExist:
        update.message.reply_text("No seed found with the provided ID.")

def default_message_handler(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    user = update.message.from_user
    telegram_id = user.id

    try:
        custom_user = User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist:
        update.message.reply_text("User not found. Please authenticate using /start.")
        return

    try:
        action = get_user_intent(user_message, custom_user)

        # Determine and execute the appropriate action
        if "list seeds" in action:
            list_seeds(update, context)
        elif "create seed" in action:
            create_seed(update, context)
        elif "search" in action:
            search(update, context)
        elif "find similar" in action:
            find_similar(update, context)
        elif "process youtube" in action:
            process_youtube(update, context)
        elif "upload file" in action:
            upload_file(update, context)
        elif "seed detail" in action:
            seed_detail(update, context)
        else:
            update.message.reply_text("I'm not sure what you want to do. Try using /submit_content, /list_seeds, /create_seed, /search, /find_similar, /process_youtube, /upload_file, or /seed_detail.")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        update.message.reply_text("An error occurred while processing your request. Please try again later.")


def main() -> None:
    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(TOKEN_TG).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_key)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)],
            AUTHENTICATED: [
                MessageHandler(filters.COMMAND, authenticated),
                CommandHandler('list_seeds', list_seeds),
                CommandHandler('create_seed', create_seed),
                CommandHandler('search', search),
                CommandHandler('find_similar', find_similar),
                CommandHandler('process_youtube', process_youtube),
                CommandHandler('upload_file', upload_file),
                CommandHandler('seed_detail', seed_detail),
                MessageHandler(filters.TEXT & ~filters.COMMAND, default_message_handler)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()