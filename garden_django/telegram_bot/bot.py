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

async def start(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    telegram_id = user.id

    try:
        custom_user = await get_user_by_telegram_id(telegram_id)
        update.message.reply_text('Welcome back! You are already authenticated.')
        return AUTHENTICATED
    except User.DoesNotExist:
        update.message.reply_text(
            'Welcome! Please send your OpenAI API key or type "password" to use a system-wide key.',
            reply_markup=ForceReply(selective=True),
        )
        return ASK_API_KEY

async def handle_api_key(update: Update, context: CallbackContext) -> int:
    api_key = update.message.text
    user = update.message.from_user
    telegram_id = user.id
    custom_user, created = await get_or_create_user(
        telegram_id=telegram_id,
        username=f'tg_{telegram_id}',
        email=f'{telegram_id}@example.com')
    if created:
        custom_user.set_unusable_password()
    
    if api_key.lower() == 'password':
        update.message.reply_text('Please enter the system password:')
        return ASK_PASSWORD
    else:
        custom_user.api_key = api_key
        await save_user(custom_user)
        update.message.reply_text('API key saved. You are now authenticated.')
        return AUTHENTICATED

async def handle_password(update: Update, context: CallbackContext) -> int:
    password = update.message.text
    user = update.message.from_user
    telegram_id = user.id
    custom_user = await get_user_by_telegram_id(telegram_id)

    if password == settings.SYSTEM_PASSWORD:
        custom_user.use_system_api_key = True
        await save_user(custom_user)
        update.message.reply_text('Password correct. You are now authenticated using the system API key.')
        return AUTHENTICATED
    else:
        update.message.reply_text('Incorrect password. Please try again.')
        return ASK_PASSWORD

async def list_seeds(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    telegram_id = user.id
    custom_user = await get_user_by_telegram_id(telegram_id)
    seeds = await filter_seeds_for_user(custom_user)
    seeds_list = "\n".join([f"{seed.id}: {seed.title}" for seed in seeds])
    update.message.reply_text(f"Here are your seeds:\n{seeds_list}")

async def seed_detail(update: Update, context: CallbackContext) -> None:
    seed_id = update.message.text.split()[-1]  # Assuming the seed ID is provided as the last word in the message
    try:
        seed_id = int(seed_id)
    except ValueError:
        update.message.reply_text("Invalid seed ID. Please provide a valid seed ID.")
        return

    user = update.message.from_user
    telegram_id = user.id
    custom_user = await get_user_by_telegram_id(telegram_id)
    
    try:
        seed = await get_seed(seed_id, custom_user)
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