#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "yt_dlp",
#   "certifi"
# ]
# ///
import argparse
import os
import ssl
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL


def download_audio(
    url: str,
    output_path: str = "~/Downloads/getsong",
    open_after: bool = False,
    convert_to_mp3: bool = False,
) -> None:
    """
    Загружает аудио с YouTube/SoundCloud используя yt-dlp.

    Args:
        url (str): URL YouTube или SoundCloud
        output_path (str): Директория для сохранения загруженного аудио
        open_after (bool): Открыть загруженный файл системным приложением после загрузки
        convert_to_mp3 (bool): Конвертировать аудио в формат MP3 (требуется FFmpeg)
    """
    # Настройка SSL контекста с сертификатами certifi
    ssl._create_default_https_context = ssl._create_unverified_context

    # Разворачиваем домашнюю директорию и создаем выходную директорию если не существует
    output_dir = Path(output_path).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Шаблон для имени выходного файла
    outtmpl = str(output_dir / "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": outtmpl,
        "progress": True,
        "quiet": False,
        "nocheckcertificate": True,
    }

    # Добавляем постпроцессор для конвертации в MP3 если запрошено
    if convert_to_mp3:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    try:
        with YoutubeDL(ydl_opts) as ydl:
            # Извлекаем информацию для получения финального имени файла
            info = ydl.extract_info(url, download=True)
            if info:
                # Получаем путь к загруженному файлу
                downloaded_file = ydl.prepare_filename(info)
                print(f"Загрузка успешно завершена!")
                print(f"Сохранено в: {downloaded_file}")

                # Открываем файл системным приложением если запрошено
                if open_after:
                    print(f"Открываем файл...")
                    subprocess.run(["open", downloaded_file])
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="Загрузка аудио с YouTube/SoundCloud используя yt-dlp"
    )
    parser.add_argument("url", help="URL YouTube или SoundCloud")
    parser.add_argument(
        "-o",
        "--open",
        action="store_true",
        help="Открыть загруженный файл системным приложением после загрузки",
    )
    parser.add_argument(
        "--mp3",
        action="store_true",
        help="Конвертировать аудио в формат MP3 (требуется FFmpeg)",
    )
    args = parser.parse_args()

    download_audio(args.url, open_after=args.open, convert_to_mp3=args.mp3)


if __name__ == "__main__":
    main()
