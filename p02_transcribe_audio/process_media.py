import argparse
import os
import subprocess


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


def main():
    parser = argparse.ArgumentParser(
        description="Process audio or video file and save as Ogg audio"
    )
    parser.add_argument("filename", help="filename to extract audio from")
    args = parser.parse_args()

    if not os.path.isfile(args.filename):
        print(f"Error: {args.filename} is not a valid file")
        return

    input_filename = args.filename
    output_filename = os.path.splitext(input_filename)[0] + ".ogg"

    convert_media_to_ogg_audio(input_filename, output_filename)


if __name__ == "__main__":
    main()
