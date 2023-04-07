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


@bot.on(events.NewMessage)
async def echo(event: events.NewMessage.Event):
    print(event.text)
    msg: tl.patched.Message = event.message

    things_to_process = []
    filename = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S%f") + "_"
    if msg.voice is not None:
        things_to_process.append(msg.voice)
        filename += str(msg.voice.id)
        print("There is a voice")
    elif msg.video_note is not None:
        things_to_process.append(msg.video_note)
        filename += str(msg.video_note.id)
        print("There is a video note")
    elif msg.file is not None:
        things_to_process.append(msg.file)
        filename += str(msg.file.id)
        print("There is a file")
    if len(things_to_process) == 0:
        print("no file to process")
        await event.respond(
            "Please send me a voice, a video message or an audio file with speech recording"
        )
        return

    def callback(current, total):
        print(
            "Downloaded",
            current,
            "out of",
            total,
            "bytes: {:.2%}".format(current / total),
        )

    filepath = "downloads/{0}_{1}".format(msg.file.id, msg.file.ext)
    print("Processing path", filepath)

    async def download_file():
        # Check if file already  exists and
        if os.path.isfile(filepath):
            # check file size
            print(os.path.getsize(filepath), msg.file.size)
            if os.path.getsize(filepath) == msg.file.size:
                print("File already exists, skipping download")
                return
        await bot.download_media(msg, filepath, progress_callback=callback)

    await download_file()

    print("done")

    print("done processing all attachments")
    """Echo the user message."""
    await event.respond("Done processing")


def main():
    """Start the bot."""
    bot.run_until_disconnected()


if __name__ == "__main__":
    main()
