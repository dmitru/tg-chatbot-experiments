"""
Launches the bot.
"""

import json
from dotenv import load_dotenv

load_dotenv()

import os

import gspread

gc = gspread.service_account(filename="google_service_key.json")
sheet_url = os.environ.get("GSPREAD_SHEET_URL")
sheet = gc.open_by_url(sheet_url)
sheet_transcribe_jobs = sheet.worksheet("transcribe_jobs")


def append_row_to_sheet(worksheet: gspread.Worksheet, row_data):
    rows_count = len(worksheet.get_all_values())
    worksheet.append_row(
        row_data, table_range="%d:%d" % (rows_count + 1, len(row_data))
    )

    return rows_count


from utils.utils import *
from datetime import datetime, timezone
from pyrogram import Client, filters
from telethon import TelegramClient, events, sync, tl, utils

TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TG_API_ID = os.environ.get("TELEGRAM_APP_ID")
TG_API_HASH = os.environ.get("TELEGRAM_APP_HASH")

MAX_FILE_SIZE = 50 * 1024 * 1024  # 250 MB

# Remember to use your own values from my.telegram.org!
bot = TelegramClient("anon", TG_API_ID, TG_API_HASH).start(bot_token=TG_BOT_TOKEN)


@bot.on(events.NewMessage)
async def on_message(event: events.NewMessage.Event):
    try:
        log_data = await process_new_message_event(event)
        if log_data is None:
            return
        print("Logging data", log_data)
        append_row_to_sheet(sheet_transcribe_jobs, list(log_data.values()))
    except Exception as error:
        log_data = {
            "date": datetime.now(timezone.utc).isoformat(),
            "error": True,
            "error_msg": str(error),
            "chat_id": event.message.chat.id,
        }
        try:
            append_row_to_sheet(sheet_transcribe_jobs, list(log_data.values()))
        except Exception as error:
            print("Error logging error", error)

        await event.respond("Sorry, there was an error processing your audio file.")


async def process_new_message_event(event: events.NewMessage.Event):
    print(event.text)
    msg: tl.patched.Message = event.message

    t_start = time.time()

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
            "Please send me a voice, a video or an audio file with speech recording"
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

    if msg.file.size > MAX_FILE_SIZE:
        await event.respond("File is too large, please send a file smaller than 250 MB")
        return

    filepath_media = "downloads/{0}_{1}".format(msg.file.id, msg.file.ext)
    filepath_audio = os.path.splitext(filepath_media)[0] + "_processed_" + ".ogg"

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

    t_after_download = time.time()

    print("Done downloading, processing audio", filepath_media, filepath_audio)
    if not os.path.isfile(filepath_audio):
        convert_to_mono_mp3(filepath_media, filepath_audio)

    t_after_conversion = time.time()

    # Read json from a file as dict
    trans_cache_file = filepath_audio + ".trans.json"
    trans_cache_hit = False
    if os.path.isfile(trans_cache_file):
        print("Transcription: reading from cache...")
        trans_result = read_json_from_filt_utf8(trans_cache_file)
        trans_cache_hit = True
    else:
        print("Transcription: starting...")
        trans_result = await transcribe_replica(filepath_audio)
        trans_cache_hit = False

    transcription = trans_result.get("transcription", "")
    detected_language = trans_result.get("detected_language", "")

    # Cache the transcription result...
    trans_cache_data = {
        "date": datetime.now(timezone.utc).isoformat(),
        "transcription": transcription,
        "detected_language": detected_language,
    }

    write_json_to_file_utf8(trans_cache_file, trans_cache_data)

    print("Transcription is done: ", transcription)

    t_after_transcription = time.time()

    media_duration = get_media_duration(filepath_audio)
    # Remove the audio file
    os.remove(filepath_audio)

    # split the transcription into chunks max 4000 characters
    transcription_chunks = make_short_parts(transcription, 4000)
    for chunk in transcription_chunks:
        print("Sending chunk...", chunk)
        await event.respond(chunk)

    t_end = time.time()

    log_data = {
        "date": datetime.now(timezone.utc).isoformat(),
        "error": False,
        "error_msg": "",
        # Message, etc
        "chat_id": msg.chat.id,
        "file_id": msg.file.id,
        "file_size": msg.file.size,
        "file_name": msg.file.name,
        "file_ext": msg.file.ext,
        "file_duration": media_duration,
        # Transcription
        "trans_cache_hit": str(trans_cache_hit),
        "trans_chunks": len(transcription_chunks),
        "trans_len": len(transcription),
        "trans_detected_language": detected_language,
        "trans_transcription": transcription[:1000],
        # Timing
        "time_download": t_after_download - t_start,
        "time_conversion": t_after_conversion - t_after_download,
        "time_transcription": t_after_transcription - t_after_conversion,
        "time_sending": t_end - t_after_transcription,
        "time_total": t_end - t_start,
        "time_ratio": media_duration / (t_end - t_start),
    }

    return log_data


def main():
    """Start the bot."""
    bot.run_until_disconnected()


if __name__ == "__main__":
    main()
