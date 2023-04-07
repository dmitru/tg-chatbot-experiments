from dotenv import load_dotenv

load_dotenv()

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
from telethon import TelegramClient, events, sync, tl, utils

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = AsyncTeleBot(BOT_TOKEN)

api_id = os.environ.get("TELEGRAM_APP_ID")
api_hash = os.environ.get("TELEGRAM_APP_HASH")

# Remember to use your own values from my.telegram.org!
bot = TelegramClient("anon", api_id, api_hash).start(bot_token=BOT_TOKEN)


def convert_media_to_ogg_audio(src_path, dest_path):
    command = [
        "ffmpeg",
        "-i",
        src_path,
        "-vn",
        "-c:a",
        "libvorbis",
        dest_path,
    ]
    result = subprocess.run(command, capture_output=True)

    if result.returncode != 0:
        print(f"Error: failed to extract audio from {src_path}")
    else:
        print(f"Successfully extracted audio from {src_path} and saved as {dest_path}")


@bot.on(events.NewMessage)
async def echo(event: events.NewMessage.Event):
    print(event.text)
    msg: tl.patched.Message = event.message

    things_to_process = []
    if msg.voice is not None:
        things_to_process.append(msg.voice)
        print("There is a voice")
    elif msg.video_note is not None:
        things_to_process.append(msg.video_note)
        print("There is a video note")
    elif msg.file is not None:
        things_to_process.append(msg.file)
        print("There is a file")
    if len(things_to_process) == 0:
        print("no file to process")
        await event.respond(
            "Please send me a voice, a video message or an audio file with speech recording"
        )
        return

    def print_progress_cb(current, total):
        print(
            "Downloaded",
            current,
            "out of",
            total,
            "bytes: {:.2%}".format(current / total),
        )

    filepath_media = "downloads/{0}_{1}".format(msg.file.id, msg.file.ext)
    filepath_audio = os.path.splitext(filepath_media)[0] + ".ogg"

    print("Processing path", filepath_media)

    async def download_file():
        # Check if file already  exists and
        if os.path.isfile(filepath_media):
            # check file size
            print(os.path.getsize(filepath_media), msg.file.size)
            if os.path.getsize(filepath_media) == msg.file.size:
                print("File already exists, skipping download")
                return
        await bot.download_media(
            msg, filepath_media, progress_callback=print_progress_cb
        )

    await download_file()

    print("Done downloading, processing audio", filepath_media)
    if not os.path.isfile(filepath_audio):
        convert_media_to_ogg_audio(filepath_media, filepath_audio)

    print("done")

    print("done processing all attachments")
    """Echo the user message."""
    await event.respond("Done processing")


def main():
    """Start the bot."""
    bot.run_until_disconnected()


if __name__ == "__main__":
    main()
