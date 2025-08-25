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

from AppKit import NSPasteboard, NSStringPboardType
from loguru import logger

TEXT_CLIPS_PATH = Path.home() / "clipmon" / "text"


def main():
    logger.info("🚀 Мониторинг буфера обмена...")
    monitor_clipboard()


def monitor_clipboard(interval: int = 5):
    last_content = None
    try:
        while True:
            current_content = get_clipboard_content()
            if current_content != last_content:
                if current_content:
                    save_text_clip(current_content)
                last_content = current_content
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("🛑 Мониторинг буфера обмена остановлен пользователем.")


def get_clipboard_content():
    pb = NSPasteboard.generalPasteboard()
    content = pb.stringForType_(NSStringPboardType)
    return content if content is not None else ""


def save_text_clip(text: str):
    TEXT_CLIPS_PATH.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    clip_path = TEXT_CLIPS_PATH / f"clip_{timestamp}.txt"

    with open(clip_path, "w", encoding="utf-8") as f:
        f.write(text)

    logger.info(f"✅ Текст из буфера сохранён в {clip_path}")


if __name__ == "__main__":
    main()
