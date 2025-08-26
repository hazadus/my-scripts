#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "pyobjc",
#   "loguru",
# ]
# ///
"""
Скрипт мониторит буфер обмена MacOS на наличие новых текстовых данных и сохраняет их в файлы.
"""
import time
from datetime import datetime
from pathlib import Path

from AppKit import NSPasteboard, NSPasteboardTypePNG, NSStringPboardType
from loguru import logger

TEXT_CLIPS_PATH = Path.home() / "clipmon" / "text"
PNG_CLIPS_PATH = Path.home() / "clipmon" / "images"


def main():
    logger.info("🚀 Мониторинг буфера обмена...")
    monitor_clipboard()


def monitor_clipboard(interval: int = 5):
    last_content = None
    try:
        while True:
            current_content, extension = get_clipboard_content()
            if current_content != last_content:
                process_content(current_content, extension)
                last_content = current_content
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("🛑 Мониторинг буфера обмена остановлен пользователем.")


def process_content(content, extension):
    if content is None:
        return

    match extension:
        case "txt":
            save_text_clip(content)
        case "png":
            save_png_clip(content)


def get_clipboard_content():
    pb = NSPasteboard.generalPasteboard()
    content = None
    file_extension = None

    if NSPasteboardTypePNG in pb.types():
        data = pb.dataForType_(NSPasteboardTypePNG)
        if data:
            content = data
            file_extension = "png"
    elif NSStringPboardType in pb.types():
        text = pb.stringForType_(NSStringPboardType)
        if text:
            content = text
            file_extension = "txt"

    return content, file_extension


def save_text_clip(text: str):
    TEXT_CLIPS_PATH.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clip_path = TEXT_CLIPS_PATH / f"clip_{timestamp}.txt"

    with open(clip_path, "w", encoding="utf-8") as f:
        f.write(text)

    logger.info(f"✅📝 Текст сохранён в {clip_path}")


def save_png_clip(data):
    PNG_CLIPS_PATH.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clip_path = PNG_CLIPS_PATH / f"clip_{timestamp}.png"

    with open(clip_path, "wb") as f:
        f.write(data)

    logger.info(f"✅🖼️ Изображение сохранено в {clip_path}")


if __name__ == "__main__":
    main()
