#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#     "beautifulsoup4",
#     "httpx",
#     "lxml",
#     "feedparser",
# ]
# ///
"""
RSS Feed Parser

Скрипт для парсинга RSS-фидов и вывода их содержимого.
Поддерживает RSS, Atom и другие XML-форматы фидов.

Особенности:
- Парсинг RSS, Atom и других XML-форматов
- Вывод названия поста, ссылки, даты/времени публикации
- Обработка ошибок и таймаутов
- Поддержка различных кодировок
- Очистка HTML-тегов из содержимого

Примеры использования:
  %(prog)s https://www.macworld.com/feed
  %(prog)s https://www.macstories.net/feed/ --limit 10
  %(prog)s https://daverupert.com/atom.xml --markdown
  %(prog)s https://blog.cassidoo.co/rss.xml --verbose
"""

import argparse
import re
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup


class RSSParser:
    """Парсер для RSS и Atom фидов."""

    def __init__(self, timeout: float = 30.0, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def parse_feed(self, url: str) -> Dict[str, Any]:
        """Парсит RSS/Atom фид и возвращает структурированные данные."""
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(
                    timeout=self.timeout, headers=self.headers, http2=False
                ) as client:
                    response = client.get(url)
                    response.raise_for_status()

                    # Используем feedparser для парсинга
                    feed = feedparser.parse(url)

                    if feed.bozo:
                        print(
                            f"Предупреждение: Фид {url} содержит ошибки",
                            file=sys.stderr,
                        )

                    return self._parse_feedparser_result(feed, url)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    print(
                        f"Ошибка: Слишком много запросов к {url} (429)", file=sys.stderr
                    )
                elif e.response.status_code == 403:
                    print(f"Ошибка: Доступ запрещен к {url} (403)", file=sys.stderr)
                elif e.response.status_code == 404:
                    print(f"Ошибка: Лента не найдена {url} (404)", file=sys.stderr)
                else:
                    print(
                        f"HTTP ошибка {e.response.status_code} при загрузке {url}",
                        file=sys.stderr,
                    )
                return {"error": f"HTTP {e.response.status_code}"}

            except (
                httpx.TimeoutException,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
            ) as e:
                if attempt < self.max_retries:
                    print(
                        f"Таймаут для {url}, попытка {attempt + 1}/{self.max_retries + 1}...",
                        file=sys.stderr,
                    )
                    continue
                else:
                    print(f"Таймаут при загрузке ленты {url}: {e}", file=sys.stderr)
                    return {"error": "Timeout"}

            except httpx.ConnectError as e:
                if attempt < self.max_retries:
                    print(
                        f"Ошибка подключения к {url}, попытка {attempt + 1}/{self.max_retries + 1}...",
                        file=sys.stderr,
                    )
                    continue
                else:
                    print(f"Ошибка подключения к {url}: {e}", file=sys.stderr)
                    return {"error": "Connection error"}

            except Exception as e:
                print(
                    f"Неожиданная ошибка при обработке ленты {url}: {e}",
                    file=sys.stderr,
                )
                return {"error": str(e)}

        return {"error": "Max retries exceeded"}

    def _parse_feedparser_result(self, feed, url: str) -> Dict[str, Any]:
        """Парсит результат feedparser."""
        try:
            feed_info = {
                "type": feed.get("version", "Unknown"),
                "url": url,
                "title": feed.feed.get("title", ""),
                "description": feed.feed.get("description", ""),
                "link": feed.feed.get("link", ""),
                "items": [],
            }

            # Обрабатываем элементы фида
            for entry in feed.entries:
                item_data = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": entry.get("summary", ""),
                    "pub_date": entry.get("published", ""),
                    "guid": entry.get("id", ""),
                    "author": entry.get("author", ""),
                    "category": (
                        entry.get("tags", [{}])[0].get("term", "")
                        if entry.get("tags")
                        else ""
                    ),
                }

                # Парсим дату публикации
                if entry.get("published_parsed"):
                    item_data["parsed_date"] = datetime(*entry.published_parsed[:6])
                elif entry.get("updated_parsed"):
                    item_data["parsed_date"] = datetime(*entry.updated_parsed[:6])

                feed_info["items"].append(item_data)

            return feed_info

        except Exception as e:
            return {"error": f"Feed parsing error: {e}"}

    def _parse_rss(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Парсит RSS фид."""
        feed_info = {
            "type": "RSS",
            "url": url,
            "title": "",
            "description": "",
            "link": "",
            "items": [],
        }

        # Информация о фиде
        channel = soup.find("channel")
        if channel:
            feed_info["title"] = self._get_text(channel.find("title"))
            feed_info["description"] = self._get_text(channel.find("description"))
            feed_info["link"] = self._get_text(channel.find("link"))

        # Элементы фида
        items = soup.find_all("item")
        for item in items:
            item_data = {
                "title": self._get_text(item.find("title")),
                "link": self._get_text(item.find("link")),
                "description": self._get_text(item.find("description")),
                "pub_date": self._get_text(item.find("pubDate")),
                "guid": self._get_text(item.find("guid")),
                "author": self._get_text(item.find("author")),
                "category": self._get_text(item.find("category")),
            }

            # Парсим дату публикации
            if item_data["pub_date"]:
                item_data["parsed_date"] = self._parse_date(item_data["pub_date"])

            feed_info["items"].append(item_data)

        return feed_info

    def _parse_atom(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Парсит Atom фид."""
        feed_info = {
            "type": "Atom",
            "url": url,
            "title": "",
            "subtitle": "",
            "link": "",
            "items": [],
        }

        # Информация о фиде
        feed = soup.find("feed")
        if feed:
            feed_info["title"] = self._get_text(feed.find("title"))
            feed_info["subtitle"] = self._get_text(feed.find("subtitle"))

            # Ссылка на сайт
            link_elem = feed.find("link", rel="alternate")
            if not link_elem:
                link_elem = feed.find("link")
            if link_elem:
                feed_info["link"] = link_elem.get("href", "")

        # Элементы фида
        entries = soup.find_all("entry")
        for entry in entries:
            entry_data = {
                "title": self._get_text(entry.find("title")),
                "link": "",
                "summary": self._get_text(entry.find("summary")),
                "content": self._get_text(entry.find("content")),
                "published": self._get_text(entry.find("published")),
                "updated": self._get_text(entry.find("updated")),
                "author": "",
                "category": "",
            }

            # Ссылка на пост
            link_elem = entry.find("link", rel="alternate")
            if not link_elem:
                link_elem = entry.find("link")
            if link_elem:
                entry_data["link"] = link_elem.get("href", "")

            # Автор
            author_elem = entry.find("author")
            if author_elem:
                entry_data["author"] = self._get_text(author_elem.find("name"))

            # Категория
            category_elem = entry.find("category")
            if category_elem:
                entry_data["category"] = category_elem.get("term", "")

            # Парсим дату публикации
            if entry_data["published"]:
                entry_data["parsed_date"] = self._parse_date(entry_data["published"])
            elif entry_data["updated"]:
                entry_data["parsed_date"] = self._parse_date(entry_data["updated"])

            feed_info["items"].append(entry_data)

        return feed_info

    def _get_text(self, element) -> str:
        """Извлекает текст из XML элемента."""
        if element is None:
            return ""

        # Убираем HTML-теги
        text = str(element)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Парсит строку даты в datetime объект."""
        if not date_str:
            return None

        # Убираем лишние пробелы
        date_str = date_str.strip()

        # Популярные форматы дат
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
            "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 с названием зоны
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601
            "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC
            "%Y-%m-%dT%H:%M:%S",  # ISO 8601 без зоны
            "%Y-%m-%d %H:%M:%S",  # Простой формат
            "%Y-%m-%d",  # Только дата
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Если не удалось распарсить, возвращаем None
        return None


def print_feed_info(
    feed_data: Dict[str, Any],
    limit: Optional[int] = None,
    markdown: bool = False,
    verbose: bool = False,
) -> None:
    """Выводит информацию о фиде."""
    if "error" in feed_data:
        print(f"Ошибка: {feed_data['error']}")
        return

    if markdown:
        print_feed_markdown(feed_data, limit)
    else:
        print_feed_text(feed_data, limit, verbose)


def print_feed_text(
    feed_data: Dict[str, Any], limit: Optional[int] = None, verbose: bool = False
) -> None:
    """Выводит информацию о фиде в текстовом формате."""
    print(f"📰 {feed_data['title'] or 'Без названия'}")
    print(f"🔗 {feed_data['url']}")
    if feed_data.get("link"):
        print(f"🌐 {feed_data['link']}")
    if feed_data.get("description"):
        print(f"📝 {feed_data['description']}")
    print(f"📊 Тип: {feed_data['type']}")
    print(f"📅 Всего постов: {len(feed_data['items'])}")
    print("=" * 60)

    items = feed_data["items"]
    if limit:
        items = items[:limit]

    for i, item in enumerate(items, 1):
        print(f"\n{i}. {item['title'] or 'Без названия'}")

        if item.get("link"):
            print(f"   🔗 {item['link']}")

        if item.get("parsed_date"):
            print(f"   📅 {item['parsed_date'].strftime('%Y-%m-%d %H:%M:%S')}")
        elif item.get("pub_date") or item.get("published"):
            date_str = item.get("pub_date") or item.get("published")
            print(f"   📅 {date_str}")

        if verbose and (item.get("description") or item.get("summary")):
            desc = item.get("description") or item.get("summary")
            if desc:
                # Ограничиваем длину описания
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                print(f"   💬 {desc}")

        if verbose and item.get("author"):
            print(f"   👤 {item['author']}")

        if verbose and item.get("category"):
            print(f"   🏷️  {item['category']}")


def print_feed_markdown(feed_data: Dict[str, Any], limit: Optional[int] = None) -> None:
    """Выводит информацию о фиде в формате Markdown."""
    print(f"# {feed_data['title'] or 'Без названия'}")
    print()
    print(f"**URL фида:** {feed_data['url']}")
    if feed_data.get("link"):
        print(f"**Сайт:** {feed_data['link']}")
    if feed_data.get("description"):
        print(f"**Описание:** {feed_data['description']}")
    print(f"**Тип:** {feed_data['type']}")
    print(f"**Всего постов:** {len(feed_data['items'])}")
    print()
    print("---")
    print()

    items = feed_data["items"]
    if limit:
        items = items[:limit]

    for i, item in enumerate(items, 1):
        print(f"## {i}. {item['title'] or 'Без названия'}")
        print()

        if item.get("link"):
            print(f"[🔗 Открыть пост]({item['link']})")
            print()

        if item.get("parsed_date"):
            print(
                f"**Дата публикации:** {item['parsed_date'].strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif item.get("pub_date") or item.get("published"):
            date_str = item.get("pub_date") or item.get("published")
            print(f"**Дата публикации:** {date_str}")

        if item.get("description") or item.get("summary"):
            desc = item.get("description") or item.get("summary")
            if desc:
                print()
                print(f"**Описание:** {desc}")

        if item.get("author"):
            print(f"**Автор:** {item['author']}")

        if item.get("category"):
            print(f"**Категория:** {item['category']}")

        print()
        print("---")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Парсер RSS-фидов с выводом названия поста, ссылки и даты публикации",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s https://www.macworld.com/feed
  %(prog)s https://www.macstories.net/feed/ --limit 5
  %(prog)s https://daverupert.com/atom.xml --markdown
  %(prog)s https://blog.cassidoo.co/rss.xml --verbose --limit 10
        """,
    )

    parser.add_argument("url", help="URL RSS-фида для парсинга")

    parser.add_argument(
        "--limit", "-l", type=int, help="Ограничить количество выводимых постов"
    )

    parser.add_argument(
        "--markdown",
        "-m",
        action="store_true",
        help="Выводить результат в формате Markdown",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Показать дополнительную информацию (автор, категория, описание)",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Таймаут для HTTP-запросов в секундах (по умолчанию: 30)",
    )

    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Количество повторных попыток при ошибках (по умолчанию: 2)",
    )

    args = parser.parse_args()

    # Валидация URL
    try:
        parsed_url = urlparse(args.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            print("Ошибка: Некорректный URL", file=sys.stderr)
            sys.exit(1)
    except Exception:
        print("Ошибка: Некорректный URL", file=sys.stderr)
        sys.exit(1)

    # Создаем парсер
    parser = RSSParser(timeout=args.timeout, max_retries=args.retries)

    # Парсим фид
    print(f"Загружаю фид: {args.url}")
    feed_data = parser.parse_feed(args.url)

    # Выводим результат
    print_feed_info(feed_data, args.limit, args.markdown, args.verbose)


if __name__ == "__main__":
    main()
