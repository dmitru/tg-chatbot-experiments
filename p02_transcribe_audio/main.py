from dotenv import load_dotenv

load_dotenv()

import argparse

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


def convert_media_to_ogg_audio(src_path, dest_path, format="ogg"):
    # convert media file to mp4 with ffmpeg
    command = []
    if format == "ogg":
        command = [
            "ffmpeg",
            "-i",
            src_path,
            "-vn",
            "-c:a",
            "libvorbis",
            dest_path,
        ]
    elif format == "mp3":
        command = [
            "ffmpeg",
            "-i",
            src_path,
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ac",
            "1",
            "-ar",
            "16000",
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
    filepath_audio = os.path.splitext(filepath_media)[0] + "_processed_" + ".mp3"

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

    print("Done downloading, processing audio", filepath_media, filepath_audio)
    # if not os.path.isfile(filepath_audio):
    # convert_media_to_ogg_audio(filepath_media, filepath_audio, format="mp3")
    convert_to_mono_mp3(filepath_media, filepath_audio)

    chunks = split_mp3_by_length(filepath_audio, 30)
    print("Chunks", chunks)
    # for chunk in [chunks[0]]:
    #     print("Chunk file = ", chunk)
    #     # TODO: use the audio file to transcribe the speech
    print("Start transcribing...")
    transcription = await transcribe_replica(filepath_audio)
    print("Transcription is done: ", transcription)

    # split the transcription into chunks max 4000 characters
    transcription_chunks = make_short_parts(transcription, 4000)
    for chunk in transcription_chunks:
        print("Sending chunk...", chunk)
        await event.respond(chunk)


def main():
    """Start the bot."""
    bot.run_until_disconnected()


if __name__ == "__main__":
    main()
