#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#     "feedparser",
#     "requests",
# ]
# ///
"""
RSS OPML Parser

Скрипт для работы с OPML файлами RSS лент.
"""

import argparse
import xml.etree.ElementTree as ET
import sys
from pathlib import Path
import feedparser
from datetime import datetime, timedelta
import time
import requests


# MARK: main
def main():
    parser = argparse.ArgumentParser(
        description="Парсер OPML файлов для RSS лент",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s feeds.opml --list              # Показать список всех RSS лент
  %(prog)s feeds.opml -l                  # Короткая форма флага --list
  %(prog)s feeds.opml --read 2025-01-15   # Показать посты за 15 января 2025
        """,
    )

    parser.add_argument("opml_file", help="Путь к OPML файлу")

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Показать список всех RSS URL из файла",
    )

    parser.add_argument(
        "--read",
        metavar="YYYY-MM-DD",
        help="Вывести посты из всех лент за указанную дату (формат: YYYY-MM-DD)",
    )

    args = parser.parse_args()

    # Проверяем существование файла
    opml_path = Path(args.opml_file)
    if not opml_path.exists():
        print(f"Ошибка: Файл '{args.opml_file}' не найден", file=sys.stderr)
        sys.exit(1)

    # Парсим OPML файл
    feeds = parse_opml(file_path=args.opml_file)

    # Выполняем действие в зависимости от флагов
    if args.list:
        list_feeds(feeds=feeds)
    elif args.read:
        read_posts_for_date(feeds, args.read)
    else:
        # Если никакие флаги не указаны, показываем краткую справку
        print(f"Файл '{args.opml_file}' содержит {len(feeds)} RSS лент.")
        print("Используйте флаг --list для просмотра списка лент.")
        print("Используйте флаг --read YYYY-MM-DD для чтения постов за дату.")
        print("Для подробной справки используйте --help")


# MARK: parse_opml
def parse_opml(
    *,
    file_path: str,
):
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


# MARK: list_feeds
def list_feeds(
    *,
    feeds: list[dict],
):
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


# MARK: parse_date_argument
def parse_date_argument(
    *,
    date_str: str,
):
    """
    Парсит строку даты в формате YYYY-MM-DD.

    Args:
        date_str (str): Строка даты в формате YYYY-MM-DD

    Returns:
        tuple: (start_datetime, end_datetime) для указанных суток
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        start_datetime = date_obj
        end_datetime = date_obj + timedelta(days=1)
        return start_datetime, end_datetime
    except ValueError:
        print(
            f"Ошибка: Неверный формат даты '{date_str}'. Используйте формат YYYY-MM-DD",
            file=sys.stderr,
        )
        sys.exit(1)


# MARK: get_feed_posts
def get_feed_posts(
    *,
    url: str,
    start_date: datetime,
    end_date: datetime,
):
    """
    Получает посты из RSS ленты за указанный период.

    Args:
        url (str): URL RSS ленты
        start_date (datetime): Начало периода
        end_date (datetime): Конец периода

    Returns:
        list: Список постов за указанный период
    """
    try:
        # Устанавливаем таймаут для запроса
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Парсим RSS ленту
        feed = feedparser.parse(response.content)

        posts = []
        for entry in feed.entries:
            # Получаем дату публикации
            published_time = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_time = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published_time = datetime(*entry.updated_parsed[:6])

            # Проверяем, попадает ли пост в указанный период
            if published_time and start_date <= published_time < end_date:
                post_info = {
                    "title": entry.get("title", "Без названия"),
                    "link": entry.get("link", ""),
                    "published": published_time,
                    "feed_title": feed.feed.get("title", "Неизвестная лента"),
                    "description": entry.get("summary", ""),
                }
                posts.append(post_info)

        return posts

    except requests.RequestException as e:
        print(f"Ошибка при загрузке ленты {url}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Ошибка при обработке ленты {url}: {e}", file=sys.stderr)
        return []


# MARK: read_posts_for_date
def read_posts_for_date(feeds: list[dict], date_str: str):
    """
    Читает посты из всех лент за указанную дату.

    Args:
        feeds (list): Список RSS лент
        date_str (str): Дата в формате YYYY-MM-DD
    """
    start_date, end_date = parse_date_argument(date_str=date_str)

    print(f"Поиск постов за {date_str}...")
    print("-" * 50)

    all_posts = []

    for feed in feeds:
        print(f"Обрабатываем ленту: {feed['title']}")
        posts = get_feed_posts(
            url=feed["url"],
            start_date=start_date,
            end_date=end_date,
        )
        all_posts.extend(posts)
        time.sleep(0.5)  # Небольшая задержка между запросами

    # Сортируем посты по дате (от старых к новым)
    all_posts.sort(key=lambda x: x["published"])

    print(f"\nНайдено {len(all_posts)} постов за {date_str}:")
    print("=" * 50)

    if not all_posts:
        print("Посты за указанную дату не найдены.")
        return

    for post in all_posts:
        print(f"\n[{post['published'].strftime('%H:%M')}] {post['feed_title']}")
        print(f"  {post['title']}")
        if post["link"]:
            print(f"  Ссылка: {post['link']}")
        if post["description"]:
            # Ограничиваем длину описания
            desc = post["description"][:200]
            if len(post["description"]) > 200:
                desc += "..."
            print(f"  Описание: {desc}")


if __name__ == "__main__":
    main()
