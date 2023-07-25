import datetime
import json
import os
import re
import subprocess
import time
import traceback
import asyncio
import telebot
import math
import openai
import replicate
from pyrogram import Client
from datetime import datetime, timezone

from telebot.async_telebot import AsyncTeleBot
import telebot

# Read .env file into os.environ

from dotenv import load_dotenv

load_dotenv()

TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = AsyncTeleBot(TG_BOT_TOKEN)

REPLICATE_MODEL_NAME = "large-v2"


replicate_model = replicate.models.get("openai/whisper")
replicate_model_version = replicate_model.versions.get(
    "e39e354773466b955265e969568deb7da217804d8e771ea8c9cd0cef6591f8bc"
)
openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Client(
    "speech2text_bot",
    api_id=os.environ.get("TELEGRAM_APP_ID"),
    api_hash=os.environ.get("TELEGRAM_APP_HASH"),
    bot_token=TG_BOT_TOKEN,
)


async def transcribe_replica(file_path):
    result = {}
    # for q in range(2):
    try:
        input = {
            "audio": open(file_path, "rb"),
            "model": REPLICATE_MODEL_NAME,
        }
        prediction = replicate.predictions.create(
            version=replicate_model_version, input=input
        )

        # wait until prediciton is ready
        await asyncio.sleep(2)
        print("Prediction status: ", prediction.status)
        while True:
            if prediction.status == "succeeded":
                break
            if prediction.status == "failed":
                break
            await asyncio.sleep(4)
            print("Prediction status: ", prediction.status)
            prediction = replicate.predictions.get(prediction.id)
    except Exception as e:
        traceback.print_exc(e)
        await asyncio.sleep(2)

    print("Output: ", prediction.output)
    outp = prediction.output
    if outp is None:
        return "(none)"
    return outp


def convert_to_mono_mp3(
    source_filename, result_filename, bitrate=40, sample_rate=16000
):
    # Run ffmpeg command to convert audio file to mono MP3
    cmd = [
        "ffmpeg",
        "-i",
        source_filename,
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-ab",
        str(bitrate) + "k",
        "-f",
        "ogg",
        "-y",
        result_filename,
    ]
    subprocess.run(cmd, check=True)

    return result_filename


def get_media_duration(file_path):
    # Get input file duration using ffprobe
    duration_cmd = [
        "ffprobe",
        "-i",
        file_path,
        "-show_entries",
        "format=duration",
        "-v",
        "quiet",
        "-of",
        "csv=p=0",
    ]
    result = subprocess.run(duration_cmd, stdout=subprocess.PIPE)
    duration = float(result.stdout)
    return duration


def split_mp3_by_length(input_file, max_length):
    duration = get_media_duration(input_file)

    # Calculate number of output files needed
    num_output_files = math.ceil(duration / max_length)

    output_paths = []
    # Split input file into multiple output files of max length
    for i in range(num_output_files):
        # Set output file name with index and mp3 extension
        output_file = f"{os.path.splitext(input_file)[0]}_{i+1}.mp3"

        # Calculate start and end positions for current chunk
        start_time = i * max_length
        end_time = min((i + 1) * max_length, duration)
        duration_time = end_time - start_time

        output_paths.append(output_file)

        # Run ffmpeg command to extract chunk of input file to output file
        cmd = [
            "ffmpeg",
            "-i",
            input_file,
            "-ss",
            str(start_time),
            "-t",
            str(duration_time),
            "-c",
            "copy",
            "-y",
            output_file,
        ]
        subprocess.run(cmd, check=True)

    return output_paths


# A function to open an audio file and split it into chunks of 30 seconds
def split_audio_file(file_path, chunk_max_len_seconds=60):
    # Get the duration of the audio file
    duration = get_media_duration(file_path)
    print("Duration: ", duration)
    if duration < 0:
        return []

    # Split the audio file into chunks of chunk_max_len_seconds seconds

    parts = []
    for i in range(int(duration / chunk_max_len_seconds)):
        part_file_path = f"{file_path}_{i}.mp3"
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                file_path,
                "-ss",
                str(i * chunk_max_len_seconds),
                "-t",
                str(chunk_max_len_seconds),
                "-acodec",
                "copy",
                part_file_path,
            ]
        )
        parts.append(part_file_path)

    # Handle the last part
    if duration % chunk_max_len_seconds != 0:
        part_file_path = f"{file_path}_{int(duration / chunk_max_len_seconds)}.mp3"
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                file_path,
                "-ss",
                str(int(duration / chunk_max_len_seconds) * chunk_max_len_seconds),
                "-acodec",
                "copy",
                part_file_path,
            ]
        )
        parts.append(part_file_path)

    return parts


def get_media_duration(filename):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filename,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        media_duration = float(result.stdout)
    except Exception as e:
        media_duration = -1

        traceback.print_exc(e)

    return media_duration


def clean(s):
    s = " ".join(s.split())
    return s


def make_short_parts(text, max_length):
    if len(text) == 0:
        return [""]

    sentences = re.split(r"(?<=[.!?])\s", text)
    result = []
    current_part = ""
    for sentence in sentences:
        if len(current_part + sentence) <= max_length:
            current_part += " " + sentence
        else:
            result.append(current_part)
            current_part = sentence
    result.append(current_part)

    final_parts = []
    for part in result:
        if len(part) <= max_length:
            final_parts.append(part)
            continue
        parts = re.split(r"(?<=[,])\s", part)
        current_part = ""
        for sub_part in parts:
            if len(current_part + sub_part) <= max_length:
                current_part += " " + sub_part
            else:
                final_parts.append(current_part)
                current_part = sub_part
        final_parts.append(current_part)

    result = final_parts
    final_parts = []

    for part in result:
        if len(part) <= max_length:
            final_parts.append(part)
            continue

        parts = []
        current_part = ""
        for w in part.split():
            if w[0].isupper():
                parts.append(current_part)
                current_part = w
            else:
                current_part += " " + w
        parts.append(current_part)

        current_part = ""
        for sub_part in parts:
            if len(current_part + sub_part) <= max_length:
                current_part += " " + sub_part
            else:
                final_parts.append(current_part)
                current_part = sub_part

        final_parts.append(current_part)

    result = final_parts
    final_parts = []
    for part in result:
        if len(part) <= max_length:
            final_parts.append(part)
            continue
        words = part.split()
        current_part = ""
        for word in words:
            if len(current_part + word) <= max_length:
                current_part += " " + word
            else:
                final_parts.append(current_part)
                current_part = word
        final_parts.append(current_part)

    short_parts = []
    for p in final_parts:
        part = clean(p)
        if len(part) != 0:
            text_to_add = part[0].upper() + part[1:]
            short_parts.append(clean(text_to_add))

    return short_parts


def write_json_to_file_utf8(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False))


def read_json_from_filt_utf8(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
