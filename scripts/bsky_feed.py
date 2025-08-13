#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "atproto",
# ]
# ///
"""
Скрипт для чтения сообщений в ленте Bluesky с использованием atproto.

Особенности:
- Поддержка репостов: показывает содержимое исходного поста с указанием,
  что это репост и кто его сделал
- Поддержка медиа-контента (изображения)
- Вывод в обычном текстовом формате или Markdown

Docs:
- https://github.com/MarshalX/python-atproto
- https://atproto.com/lexicons/app-bsky-feed
"""
import argparse
import datetime as dt
import re
from typing import Optional

from atproto import Client


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


def make_client(identifier: str, password: str) -> Client:
    """Создает клиент Bluesky с аутентификацией."""
    client = Client()
    client.login(identifier, password)
    return client


def strip_html(content: str) -> str:
    """Удаляет HTML-теги и декодирует сущности."""
    if not content:
        return ""
    text = re.sub(r"<[^>]+>", "", content)
    return text.strip()


def html_to_markdown(content: str) -> str:
    """Очень простой конвертер HTML Bluesky-контента в Markdown.

    Поддерживает переносы строк и гиперссылки. Остальные теги удаляются.
    """
    if not content:
        return ""
    text = content
    # Переносы строк
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*p\s*>\s*<\s*p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*p\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*p\s*>", "\n\n", text, flags=re.IGNORECASE)

    # Ссылки: <a href="URL">TEXT</a> -> [TEXT](URL)
    def _link_repl(match: re.Match) -> str:
        url = match.group(1)
        inner = match.group(2)
        inner_clean = re.sub(r"<[^>]+>", "", inner)
        return f"[{inner_clean}]({url})"

    text = re.sub(
        r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>",
        _link_repl,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Удаляем прочие теги
    text = re.sub(r"<[^>]+>", "", text)
    # Чистим лишние пустые строки
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def fetch_home_for_date(
    client: Client,
    target_date: dt.date,
) -> list[dict]:
    """Загружает сообщения из домашней ленты за указанную дату (локальная таймзона).

    Делает пагинацию назад по времени, пока встречаются посты этой даты
    (или пока лента не закончится). Ограничение по безопасности — до 1000 постов.
    """
    local_tz = dt.datetime.now().astimezone().tzinfo

    results: list[dict] = []
    cursor = None
    fetched = 0

    while True:
        try:
            # Получаем домашнюю ленту
            response = client.get_timeline(limit=50, cursor=cursor)
            if not response or not response.feed:
                break

            chunk = response.feed
            fetched += len(chunk)
            
            # Обновляем cursor для пагинации к более старым постам
            cursor = response.cursor
            
            # Отладочная информация для первого поста
            if fetched == len(chunk) and chunk:  # Только для первого чанка
                first_post = chunk[0]
                print(f"DEBUG: Структура первого поста:")
                print(f"  - Тип post: {type(first_post)}")
                print(f"  - post.post.record: {hasattr(first_post.post, 'record')}")
                if hasattr(first_post.post, 'record'):
                    print(f"  - Тип record: {type(first_post.post.record)}")
                    print(f"  - record.createdAt: {getattr(first_post.post.record, 'createdAt', 'НЕТ')}")
                    print(f"  - record.text: {getattr(first_post.post.record, 'text', 'НЕТ')}")
                    print(f"  - Доступные атрибуты record: {dir(first_post.post.record)}")
                print(f"  - post.post.author.handle: {first_post.post.author.handle}")
                print(f"  - post.post.author.displayName: {getattr(first_post.post.author, 'displayName', 'НЕТ')}")
                print(f"  - post.post.author.display_name: {getattr(first_post.post.author, 'display_name', 'НЕТ')}")
                print(f"  - Доступные атрибуты post: {dir(first_post)}")
                print(f"  - Доступные атрибуты post.post: {dir(first_post.post)}")
                print(f"  - Доступные атрибуты author: {dir(first_post.post.author)}")
                print(f"  - Проверка времени создания:")
                print(f"    - record.created_at: {getattr(first_post.post.record, 'created_at', 'НЕТ')}")
                print(f"    - record.createdAt: {getattr(first_post.post.record, 'createdAt', 'НЕТ')}")
                print(f"    - post.indexedAt: {getattr(first_post, 'indexedAt', 'НЕТ')}")
                print(f"    - post.post.indexedAt: {getattr(first_post.post, 'indexedAt', 'НЕТ')}")
                print()

            for post in chunk:
                try:
                    # Получаем время создания поста из record.createdAt
                    if not hasattr(post.post, 'record'):
                        print(f"DEBUG: Пост не имеет атрибута 'record': {type(post.post)}")
                        continue
                        
                    # Пробуем разные способы получения времени создания поста
                    created_at_str = None
                    
                    # Сначала пробуем record.created_at (с подчеркиванием)
                    if hasattr(post.post.record, 'created_at'):
                        created_at_str = post.post.record.created_at
                    # Если нет, пробуем record.createdAt
                    elif hasattr(post.post.record, 'createdAt'):
                        created_at_str = post.post.record.createdAt
                    # Если нет, пробуем indexedAt
                    elif hasattr(post.post, 'indexedAt'):
                        created_at_str = post.post.indexedAt
                    # Если и этого нет, пробуем post.indexedAt
                    elif hasattr(post.post, 'indexedAt'):
                        created_at_str = post.post.indexedAt
                    
                    if not created_at_str:
                        print(f"DEBUG: Пост не имеет времени создания. Record атрибуты: {dir(post.post.record)}")
                        print(f"DEBUG: Post атрибуты: {dir(post.post)}")
                        continue
                        
                    created_at = dt.datetime.fromisoformat(
                        created_at_str.replace('Z', '+00:00')
                    ).astimezone(local_tz)
                    post_date = created_at.date()
                    
                    if post_date == target_date:
                        # Преобразуем в формат, совместимый с логикой вывода
                        post_dict = {
                            "created_at": created_at,
                            "author": post.post.author.handle,
                            "display_name": getattr(post.post.author, 'displayName', None) or getattr(post.post.author, 'display_name', None) or post.post.author.handle,
                            "content": getattr(post.post.record, 'text', ''),
                            "uri": post.post.uri,
                            "cid": post.post.cid,
                            "is_repost": hasattr(post, "reason") and post.reason is not None,
                            "repost_author": getattr(post.reason.by, 'handle', None) if hasattr(post, "reason") and post.reason and hasattr(post.reason, 'by') else None,
                            "repost_display_name": getattr(post.reason.by, 'displayName', None) or getattr(post.reason.by, 'display_name', None) or getattr(post.reason.by, 'handle', None) if hasattr(post, "reason") and post.reason and hasattr(post.reason, 'by') else None,
                            "media": [],
                            "url": f"https://bsky.app/profile/{post.post.author.handle}/post/{post.post.uri.split('/')[-1]}"
                        }
                        
                        # Добавляем медиа, если есть
                        if hasattr(post.post, "embed") and post.post.embed:
                            if hasattr(post.post.embed, "images"):
                                for img in post.post.embed.images:
                                    post_dict["media"].append({
                                        "type": "image",
                                        "url": img.fullsize,
                                        "alt": img.alt or "image"
                                    })
                        
                        results.append(post_dict)
                except Exception as e:
                    print(f"DEBUG: Ошибка при обработке поста: {e}")
                    print(f"DEBUG: Структура поста: {dir(post)}")
                    continue

            # Критерий остановки пагинации: самый старый пост в чанке стал старее даты
            if chunk:
                oldest_created_str = None
                last_post = chunk[-1]
                
                # Пробуем разные способы получения времени создания поста
                if hasattr(last_post.post.record, 'created_at'):
                    oldest_created_str = last_post.post.record.created_at
                elif hasattr(last_post.post.record, 'createdAt'):
                    oldest_created_str = last_post.post.record.createdAt
                elif hasattr(last_post, 'indexedAt'):
                    oldest_created_str = last_post.indexedAt
                elif hasattr(last_post.post, 'indexedAt'):
                    oldest_created_str = last_post.post.indexedAt
                
                if oldest_created_str:
                    oldest_created = dt.datetime.fromisoformat(
                        oldest_created_str.replace('Z', '+00:00')
                    ).astimezone(local_tz).date()
                    if oldest_created < target_date:
                        break

            if fetched >= 1000:
                break

        except Exception as e:
            print(f"Ошибка при загрузке ленты: {e}")
            break

    # Сортируем от старых к новым
    results.sort(key=lambda s: s["created_at"])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Показать посты из домашней ленты Bluesky за указанную дату",
    )
    parser.add_argument(
        "date",
        nargs="?",
        help="Дата в формате YYYY-MM-DD (по умолчанию — сегодня)",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Выводить посты в формате Markdown (ссылки и изображения)",
    )
    parser.add_argument(
        "--identifier",
        required=True,
        help="Идентификатор Bluesky (например: username.bsky.social)",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="App Password для Bluesky",
    )
    args = parser.parse_args()

    target_date = parse_date(args.date)
    client = make_client(args.identifier, args.password)
    posts = fetch_home_for_date(client, target_date)

    if not posts:
        print(f"Постов за {target_date.isoformat()} не найдено.")
        return

    print(f"Постов за {target_date.isoformat()}: {len(posts)}\n")

    for post in posts:
        created_at = post["created_at"].strftime("%H:%M")
        user = post["author"]
        display_name = post["display_name"] or user
        
        # Проверяем, является ли это репостом
        is_repost = post.get("is_repost", False)
        
        if args.markdown:
            print("----")
            if is_repost:
                # Это репост - показываем информацию о репосте
                repost_user = post.get("repost_author", "unknown")
                repost_display_name = post.get("repost_display_name") or repost_user
                print(f"**🔄 {created_at} 👤 @{user} ({display_name}) репостнул пост от @{repost_user} ({repost_display_name})**")
                body = html_to_markdown(post.get("content", "")) or "[медиа/без текста]"
                print(f"💬 {body}")
                # Медиа (изображения)
                for media in post.get("media", []):
                    if media.get("type") == "image":
                        alt = media.get("alt", "image")
                        url = media.get("url")
                        if url:
                            print(f"\n![{alt}]({url})")
                # Ссылка на оригинал репостнутого поста
                if post.get("url"):
                    print(f"\n[Открыть оригинальный пост]({post['url']})")
            else:
                # Обычный пост
                print(f"**🕒 {created_at} 👤 @{user} ({display_name})**")
                body = html_to_markdown(post.get("content", "")) or "[медиа/без текста]"
                print(f"💬 {body}")
                # Медиа (изображения)
                for media in post.get("media", []):
                    if media.get("type") == "image":
                        alt = media.get("alt", "image")
                        url = media.get("url")
                        if url:
                            print(f"\n![{alt}]({url})")
                # Ссылка на оригинал поста
                if post.get("url"):
                    print(f"\n[Открыть пост]({post['url']})")
            print()
        else:
            if is_repost:
                # Это репост - показываем информацию о репосте
                repost_user = post.get("repost_author", "unknown")
                text = strip_html(post.get("content", "")) or "[медиа/без текста]"
                print(f"{created_at} @{user} ({display_name}) репостнул от @{repost_user}: {text}")
            else:
                # Обычный пост
                text = strip_html(post.get("content", "")) or "[медиа/без текста]"
                print(f"{created_at} @{user} ({display_name}): {text}")


if __name__ == "__main__":
    main()