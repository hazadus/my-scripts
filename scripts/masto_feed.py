#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "Mastodon.py",
# ]
# ///
"""
Скрипт для чтения сообщений в ленте Mastodon с использованием Mastodon.py.

Docs:
- https://github.com/halcy/Mastodon.py?tab=readme-ov-file
- https://mastodonpy.readthedocs.io/en/stable/
"""
import argparse
import datetime as dt
import html
import re

from mastodon import Mastodon


ACCESS_TOKEN_FILE = "toot_usercred.secret"


def parse_date(date_str: str | None) -> dt.date:
    """Возвращает дату из строки YYYY-MM-DD или текущую, если строка не задана."""
    if not date_str:
        return dt.date.today()
    try:
        return dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(
            "Неверный формат даты. Используйте YYYY-MM-DD, например 2024-10-31"
        )


def make_client() -> Mastodon:
    return Mastodon(
        access_token=ACCESS_TOKEN_FILE,
        api_base_url="https://fosstodon.org",
    )


def strip_html(content: str) -> str:
    # Удаляем HTML-теги и декодируем сущности
    text = re.sub(r"<[^>]+>", "", content)
    return html.unescape(text).strip()


def fetch_home_for_date(
    mastodon: Mastodon,
    target_date: dt.date,
) -> list[dict]:
    """Загружает сообщения из домашней ленты за указанную дату (локальная таймзона).

    Делает пагинацию назад по времени, пока встречаются посты этой даты
    (или пока лента не закончится). Ограничение по безопасности — до 1000 постов.
    """
    local_tz = dt.datetime.now().astimezone().tzinfo

    results: list[dict] = []
    max_id = None
    fetched = 0

    while True:
        chunk = mastodon.timeline_home(limit=40, max_id=max_id)
        if not chunk:
            break

        fetched += len(chunk)
        # Обновляем max_id для пагинации к более старым постам
        max_id = chunk[-1]["id"]

        for status in chunk:
            created_at = status["created_at"].astimezone(local_tz)
            status_date = created_at.date()
            if status_date == target_date:
                results.append(status)
            # Если пост старее нужной даты, можно продолжать пагинацию,
            # но добавлять уже нечего. Продолжим цикл, чтобы убедиться,
            # что не пропустили границу даты внутри чанка.

        # Критерий остановки пагинации: самый старый пост в чанке стал старее даты
        oldest_created = chunk[-1]["created_at"].astimezone(local_tz).date()
        if oldest_created < target_date:
            break

        if fetched >= 1000:
            break

    # Сортируем от старых к новым
    results.sort(key=lambda s: s["created_at"])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Показать туиты (посты) из домашней ленты за указанную дату",
    )
    parser.add_argument(
        "date",
        nargs="?",
        help="Дата в формате YYYY-MM-DD (по умолчанию — сегодня)",
    )
    args = parser.parse_args()

    target_date = parse_date(args.date)
    mastodon = make_client()
    statuses = fetch_home_for_date(mastodon, target_date)

    if not statuses:
        print(f"Постов за {target_date.isoformat()} не найдено.")
        return

    print(f"Постов за {target_date.isoformat()}: {len(statuses)}")

    for status in statuses:
        created_at = status["created_at"].astimezone().strftime("%H:%M")
        user = status["account"]["acct"]
        text = strip_html(status["content"]) or "[медиа/без текста]"
        print(f"{created_at} @{user}: {text}")


if __name__ == "__main__":
    main()
