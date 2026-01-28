#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#     "httpx",
# ]
# ///
"""
Readwise Articles Search

Скрипт для поиска по архиву статей из Readwise.
Поиск по тэгам, названию, описанию и highlights.

Примеры использования:

    # Показать список всех тэгов с количеством статей
    ./readwise_search.py --tags

    # Показать список всех источников (авторов/сайтов)
    ./readwise_search.py --sources

    # Поиск по ключевому слову в названии, описании, заметках и highlights
    ./readwise_search.py --search "python"
    ./readwise_search.py -s "машинное обучение"

    # Фильтр по тэгу (частичное совпадение, регистронезависимо)
    ./readwise_search.py --tag "Go"
    ./readwise_search.py -t "llm"

    # Фильтр по источнику (автору/сайту)
    ./readwise_search.py --source "хабр"
    ./readwise_search.py --source "Simon Willison"

    # Комбинированный поиск: по тексту, тэгу и источнику
    ./readwise_search.py --search "API" --tag "FastAPI"
    ./readwise_search.py -s "testing" -t "python" --source "pytest"

    # Ограничение количества результатов (по умолчанию: 20)
    ./readwise_search.py --search "docker" --limit 5
    ./readwise_search.py -s "kubernetes" -l 50

    # Полный пример с комбинацией параметров
    ./readwise_search.py --search "auth" --tag "Django" --source "realpython" --limit 10
"""

import argparse
import sys
from typing import Optional

import httpx

ARTICLES_URL = "https://raw.githubusercontent.com/hazadus/readwise-links/refs/heads/main/web/src/assets/articles.json"


def fetch_articles() -> list[dict]:
    """Загружает JSON с архивом статей."""
    try:
        response = httpx.get(ARTICLES_URL, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        print(f"Ошибка загрузки: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


def get_all_tags(articles: list[dict]) -> dict[str, int]:
    """Собирает все уникальные тэги с количеством использований."""
    tags_count: dict[str, int] = {}
    for article in articles:
        tags = article.get("tags", {})
        if isinstance(tags, dict):
            for tag_key, tag_info in tags.items():
                tag_name = (
                    tag_info.get("name", tag_key)
                    if isinstance(tag_info, dict)
                    else tag_key
                )
                tags_count[tag_name] = tags_count.get(tag_name, 0) + 1
    return dict(sorted(tags_count.items(), key=lambda x: (-x[1], x[0])))


def get_all_sources(articles: list[dict]) -> dict[str, dict]:
    """Собирает все уникальные источники с количеством статей и примером URL."""
    sources: dict[str, dict] = {}
    for article in articles:
        author = article.get("author") or article.get("site_name") or ""
        if not author:
            continue
        if author not in sources:
            source_url = article.get("source_url") or article.get("url", "")
            base_url = ""
            if source_url:
                from urllib.parse import urlparse

                parsed = urlparse(source_url)
                base_url = (
                    f"{parsed.scheme}://{parsed.netloc}"
                    if parsed.scheme
                    else parsed.netloc
                )
            sources[author] = {"count": 0, "url": base_url}
        sources[author]["count"] += 1
    return dict(sorted(sources.items(), key=lambda x: (-x[1]["count"], x[0])))


def search_articles(
    articles: list[dict],
    query: Optional[str] = None,
    tag: Optional[str] = None,
    source: Optional[str] = None,
) -> list[dict]:
    """Ищет статьи по запросу, тэгу и/или источнику."""
    results = []
    query_lower = query.lower() if query else None
    tag_lower = tag.lower() if tag else None
    source_lower = source.lower() if source else None

    for article in articles:
        if source_lower:
            article_source = (
                article.get("author") or article.get("site_name") or ""
            ).lower()
            if source_lower not in article_source:
                continue

        if tag_lower:
            tags = article.get("tags", {})
            if isinstance(tags, dict):
                tag_names = [
                    (info.get("name", key) if isinstance(info, dict) else key).lower()
                    for key, info in tags.items()
                ]
                if not any(tag_lower in t for t in tag_names):
                    continue
            else:
                continue

        if query_lower:
            searchable_text = " ".join(
                filter(
                    None,
                    [
                        article.get("title", ""),
                        article.get("summary", ""),
                        article.get("notes", ""),
                        article.get("author", ""),
                    ],
                )
            ).lower()

            highlights = article.get("highlights", [])
            if highlights:
                for h in highlights:
                    if isinstance(h, dict):
                        searchable_text += " " + (h.get("content", "") or "").lower()
                        searchable_text += " " + (h.get("notes", "") or "").lower()

            if query_lower not in searchable_text:
                continue

        results.append(article)

    return results


def format_article(article: dict) -> str:
    """Форматирует статью для вывода."""
    lines = []
    title = article.get("title", "Без названия")
    source_url = article.get("source_url") or article.get("url", "")

    lines.append(f"📖 {title}")
    if source_url:
        lines.append(f"   🔗 {source_url}")

    author = article.get("author")
    if author:
        lines.append(f"   ✍️  {author}")

    tags = article.get("tags", {})
    if isinstance(tags, dict) and tags:
        tag_names = [
            info.get("name", key) if isinstance(info, dict) else key
            for key, info in tags.items()
        ]
        lines.append(f"   🏷️  {', '.join(tag_names)}")

    summary = article.get("summary", "")
    if summary:
        if len(summary) > 512:
            summary = summary[:512] + "..."
        lines.append(f"   💬 {summary}")

    highlights = article.get("highlights", [])
    if highlights:
        lines.append(f"   📝 Highlights: {len(highlights)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Поиск по архиву статей Readwise",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s --tags                        # Показать список всех тэгов
  %(prog)s --sources                     # Показать список всех источников
  %(prog)s --search "python"             # Поиск по ключевому слову
  %(prog)s --tag "AI"                    # Фильтр по тэгу
  %(prog)s --source "habr"               # Фильтр по источнику
  %(prog)s -s "API" -t "Go" --source x   # Комбинированный поиск
  %(prog)s --limit 5                     # Ограничить количество результатов
        """,
    )

    parser.add_argument(
        "--tags",
        action="store_true",
        help="Показать список всех тэгов",
    )

    parser.add_argument(
        "--sources",
        action="store_true",
        help="Показать список всех источников (авторов/сайтов)",
    )

    parser.add_argument(
        "--search",
        "-s",
        metavar="QUERY",
        help="Поиск по названию, описанию, highlights и заметкам",
    )

    parser.add_argument(
        "--tag",
        "-t",
        metavar="TAG",
        help="Фильтр по тэгу (частичное совпадение)",
    )

    parser.add_argument(
        "--source",
        metavar="SOURCE",
        help="Фильтр по источнику/автору (частичное совпадение)",
    )

    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=20,
        help="Максимальное количество результатов (по умолчанию: 20)",
    )

    args = parser.parse_args()

    if (
        not args.tags
        and not args.sources
        and not args.search
        and not args.tag
        and not args.source
    ):
        parser.print_help()
        sys.exit(0)

    print("Загрузка архива статей...", file=sys.stderr)
    articles = fetch_articles()
    print(f"Загружено {len(articles)} статей.\n", file=sys.stderr)

    if args.tags:
        tags = get_all_tags(articles)
        print(f"Найдено {len(tags)} тэгов:\n")
        for tag_name, count in tags.items():
            print(f"  {tag_name}: {count}")
        return

    if args.sources:
        sources = get_all_sources(articles)
        print(f"Найдено {len(sources)} источников:\n")
        for source_name, info in sources.items():
            url_part = f" ({info['url']})" if info["url"] else ""
            print(f"  {source_name}: {info['count']}{url_part}")
        return

    results = search_articles(
        articles, query=args.search, tag=args.tag, source=args.source
    )

    if not results:
        print("Ничего не найдено.")
        return

    print(f"Найдено: {len(results)} статей\n")

    for article in results[: args.limit]:
        print(format_article(article))
        print("-" * 4)

    if len(results) > args.limit:
        print(
            f"\n... и ещё {len(results) - args.limit} статей. Используйте --limit для увеличения."
        )


if __name__ == "__main__":
    main()
