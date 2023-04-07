import datetime
import os
import subprocess
import time
import traceback

from utils.utils import *
from telebot.async_telebot import AsyncTeleBot
import telebot
import openai
import replicate
from datetime import datetime, timezone
from pyrogram import Client, filters
from telethon import TelegramClient, events, sync

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = AsyncTeleBot(BOT_TOKEN)

app_id = os.environ.get("TELEGRAM_APP_ID")
app_hash = os.environ.get("TELEGRAM_APP_HASH")
app = TelegramClient("session_name", app_id, app_hash, bot)

REPLICATE_MODEL_NAME = "large-v2"

replicate_model = replicate.models.get("openai/whisper")
replicate_model_version = replicate_model.versions.get(
    "e39e354773466b955265e969568deb7da217804d8e771ea8c9cd0cef6591f8bc"
)
openai.api_key = os.environ.get("OPENAI_API_KEY")

ERROR_MESSAGE_TEXT = "Sorry, something went wrong 😔"
WRONG_CONTENT_TYPE_TEXT = "Please send audio or text 🙏"
SOMETHING_WITH_TEXT_PROCESSING_TEXT = "Sorry, something wrong with OpenAI servers, send me this message again in a minute 😉"
TOO_LONG_TEXT_ERROR_TEXT = "Text is too long, send it in smaller chunks! 😊"
TOO_LONG_AUDIO_ERROR_TEXT = "Audio is too long, send it in smaller chunks! 😊"
EMPTY_AUDIO_TEXT = "Nothing to show 🙈"
EMPTY_IMG_TEXT = "Hey, sorry, I couldn't find anything on that photo 🙈"


# @bot.message_handler(commands=["start", "hello"])
# async def send_welcome(message):
#     bot.reply_to(message, "Howdy, how are you doing?")


# @bot.message_handler(content_types=["text"])
# async def handle_text(message):
#     bot.reply_to(message, "You said: " + message.text)


# @app.on_message(filters.audio | filters.video_note | filters.voice)
# async def on_audio_message(client, message):
#     print("on_audio_message 1", message)
#     file_name = await app.download_media(message)
#     print("on_audio_message 2", file_name)
#     await app.send_message(message.chat.id, "Audio received, processing...")

#     # Split audio into chunks 3 min each
#     chunks = split_audio_file(file_name, 1 * 60)
#     print(chunks)

#     text_to_answer = "✅ Audio processed, give me some time... " + file_name
#     # await pyrogram.send_chat_action(message.chat.id, "typing")
#     print(text_to_answer)

#     media_duration = get_media_duration(file_name)
#     print(media_duration)

#     if 0 > media_duration or 13 * 60 < media_duration:
#         try:
#             await app.send_to(message.chat.id, TOO_LONG_AUDIO_ERROR_TEXT)
#             print(TOO_LONG_AUDIO_ERROR_TEXT)

#         except Exception as e:
#             traceback.print_exc(e)

#         return

#     try:
#         text_to_process = ""
#         for chunk in chunks:
#             print("Processing chunk", chunk)
#             text_to_process += transcribe_replica(chunk)
#             print(text_to_process)

#         if len(clean(text_to_process)) < 2:
#             text_parts = [""]
#         else:
#             text_parts = make_short_parts(text_to_process, max_length=10000)

#         for text_to_process in text_parts:
#             if text_to_process == "":
#                 text_to_answer = "<b>🎙 Text in Audio:</b>\n\n" + EMPTY_AUDIO_TEXT
#             else:
#                 paragraphs = "\n\n".join(
#                     make_short_parts(text_to_process, max_length=350)
#                 )
#                 text_to_answer = "<b>🎙 Text in Audio:</b>\n\n" + paragraphs

#             await app.send_message(message.chat.id, text_to_answer)
#             print(text_to_answer)

#     except Exception as e:
#         await app.send_message(message, ERROR_MESSAGE_TEXT)
#         traceback.print_exc(e)

#         return


import os
import sys
import time
from collections import defaultdict

from telethon import TelegramClient, events

import logging

logging.basicConfig(level=logging.WARNING)

# "When did we last react?" dictionary, 0.0 by default
recent_reacts = defaultdict(float)


def get_env(name, message, cast=str):
    if name in os.environ:
        return os.environ[name]
    while True:
        value = input(message)
        try:
            return cast(value)
        except ValueError as e:
            print(e, file=sys.stderr)
            time.sleep(1)


def can_react(chat_id):
    # Get the time when we last sent a reaction (or 0)
    last = recent_reacts[chat_id]

    # Get the current time
    now = time.time()

    # If 10 minutes as seconds have passed, we can react
    if now - last < 10 * 60:
        # Make sure we updated the last reaction time
        recent_reacts[chat_id] = now
        return True
    else:
        return False


# Register `events.NewMessage` before defining the client.
# Once you have a client, `add_event_handler` will use this event.
@events.register(events.NewMessage)
async def handler(event):
    # There are better ways to do this, but this is simple.
    # If the message is not outgoing (i.e. someone else sent it)
    if not event.out:
        if "emacs" in event.raw_text:
            if can_react(event.chat_id):
                await event.reply("> emacs\nneeds more vim")

        elif "vim" in event.raw_text:
            if can_react(event.chat_id):
                await event.reply("> vim\nneeds more emacs")

        elif "chrome" in event.raw_text:
            if can_react(event.chat_id):
                await event.reply("> chrome\nneeds more firefox")

    # Reply always responds as a reply. We can respond without replying too
    if "shrug" in event.raw_text:
        if can_react(event.chat_id):
            await event.respond(r"¯\_(ツ)_/¯")

    # We can also use client methods from here
    client = event.client

    # If we sent the message, we are replying to someone,
    # and we said "save pic" in the message
    if event.out and event.is_reply and "save pic" in event.raw_text:
        reply_msg = await event.get_reply_message()
        replied_to_user = await reply_msg.get_input_sender()

        message = await event.reply("Downloading your profile photo...")
        file = await client.download_profile_photo(replied_to_user)
        await message.edit("I saved your photo in {}".format(file))


client = TelegramClient(
    os.environ.get("TG_SESSION", "replier"),
    get_env("TG_API_ID", "Enter your API ID: ", int),
    get_env("TG_API_HASH", "Enter your API hash: "),
    proxy=None,
)

with client:
    # This remembers the events.NewMessage we registered before
    client.add_event_handler(handler)

    print("(Press Ctrl+C to stop this)")
    client.run_until_disconnected()
