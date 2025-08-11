#!/usr/bin/env -S uv run --quiet --script
"""
RSS OPML Parser

Скрипт для работы с OPML файлами RSS лент.
"""

import argparse
import xml.etree.ElementTree as ET
import sys
from pathlib import Path


def parse_opml(file_path):
    """
    Парсит OPML файл и извлекает все RSS URL.

    Args:
        file_path (str): Путь к OPML файлу

    Returns:
        list: Список словарей с информацией о RSS лентах
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        feeds = []

        # Ищем все элементы outline с атрибутом xmlUrl
        for outline in root.findall(".//outline[@xmlUrl]"):
            feed_info = {
                "title": outline.get("title", outline.get("text", "Unknown")),
                "url": outline.get("xmlUrl"),
                "website": outline.get("htmlUrl", ""),
                "description": outline.get("description", ""),
            }
            feeds.append(feed_info)

        return feeds

    except ET.ParseError as e:
        print(f"Ошибка парсинга XML: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Файл не найден: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


def list_feeds(feeds):
    """
    Выводит список всех RSS URL.

    Args:
        feeds (list): Список с информацией о RSS лентах
    """
    if not feeds:
        print("RSS ленты не найдены в файле OPML")
        return

    print(f"Найдено {len(feeds)} RSS лент:")
    print("-" * 50)

    for i, feed in enumerate(feeds, 1):
        print(f"{i:3d}. {feed['title']}")
        print(f"     URL: {feed['url']}")
        if feed["website"]:
            print(f"     Сайт: {feed['website']}")
        if feed["description"]:
            print(f"     Описание: {feed['description']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Парсер OPML файлов для RSS лент",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s feeds.opml --list           # Показать список всех RSS лент
  %(prog)s feeds.opml -l               # Короткая форма флага --list
        """,
    )

    parser.add_argument("opml_file", help="Путь к OPML файлу")

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Показать список всех RSS URL из файла",
    )

    args = parser.parse_args()

    # Проверяем существование файла
    opml_path = Path(args.opml_file)
    if not opml_path.exists():
        print(f"Ошибка: Файл '{args.opml_file}' не найден", file=sys.stderr)
        sys.exit(1)

    # Парсим OPML файл
    feeds = parse_opml(args.opml_file)

    # Выполняем действие в зависимости от флагов
    if args.list:
        list_feeds(feeds)
    else:
        # Если никакие флаги не указаны, показываем краткую справку
        print(f"Файл '{args.opml_file}' содержит {len(feeds)} RSS лент.")
        print("Используйте флаг --list для просмотра списка лент.")
        print("Для подробной справки используйте --help")


if __name__ == "__main__":
    main()
