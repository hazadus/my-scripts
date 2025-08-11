#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "yt_dlp",
#   "certifi"
# ]
# ///
import argparse
import ssl

from yt_dlp import YoutubeDL


def download_video(
    url: str,
    output_path: str = "/Users/hazadus/Downloads/FromYouTube",
    highest_quality: bool = False,
) -> None:
    """
    Download a YouTube video using yt-dlp.

    Args:
        url (str): YouTube video URL
        output_path (str): Directory to save the downloaded video
        highest_quality (bool): Download in highest possible quality if True
    """
    # Configure SSL context with certifi certificates
    ssl._create_default_https_context = ssl._create_unverified_context

    if highest_quality:
        outtmpl = f"{output_path}/%(title)s HQ.%(ext)s"
    else:
        outtmpl = f"{output_path}/%(title)s.%(ext)s"

    ydl_opts = {
        "format": (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best" if highest_quality else "best"
        ),
        "outtmpl": outtmpl,
        "progress": True,
        "quiet": False,
        "nocheckcertificate": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Download completed successfully!")
    except Exception as e:
        print(f"Error occurred: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Download YouTube videos using yt-dlp")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-hq",
        "--highest-quality",
        action="store_true",
        help="Download in highest possible quality",
    )
    args = parser.parse_args()

    download_video(args.url, highest_quality=args.highest_quality)


if __name__ == "__main__":
    main()
