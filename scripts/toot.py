#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "Mastodon.py",
# ]
# ///
"""
Скрипт для публикации сообщений в Mastodon с использованием Mastodon.py.

Docs:
- https://github.com/halcy/Mastodon.py?tab=readme-ov-file
- https://mastodonpy.readthedocs.io/en/stable/
"""
import argparse
from mastodon import Mastodon


def get_access_token_oauth():
    """
    Получение access token через OAuth.
    Этот метод нужно запустить один раз для получения токена.
    """
    # 1. Регистрируем приложение (если не зарегистрировано)
    try:
        with open("toot_clientcred.secret", "r"):
            pass  # файл существует
    except FileNotFoundError:
        print("Регистрируем приложение...")
        Mastodon.create_app(
            "hazadus_tooter_app",
            api_base_url="https://fosstodon.org",
            to_file="toot_clientcred.secret",
        )
        print("Приложение зарегистрировано!")

    # 2. Получаем URL для авторизации
    mastodon = Mastodon(
        client_id="toot_clientcred.secret", api_base_url="https://fosstodon.org"
    )

    auth_url = mastodon.auth_request_url()
    print(f"\n1. Перейдите по ссылке для авторизации:")
    print(f"   {auth_url}")
    print("\n2. Авторизуйтесь в Mastodon")
    print("3. Скопируйте код авторизации из браузера")

    code = input("\n4. Введите код авторизации: ").strip()

    try:
        # 3. Получаем access token
        access_token = mastodon.log_in(code=code, to_file="toot_usercred.secret")
        print(f"\nТокен успешно получен и сохранен в toot_usercred.secret")
        print(f"Ваш access token: {access_token}")
        return access_token
    except Exception as e:
        print(f"Ошибка при получении токена: {e}")
        return None


def publish_message(
    *,
    message: str,
) -> None:
    """
    Публикует сообщение в Mastodon.

    Args:
        message (str): Сообщение для публикации
    """
    if not message or message.strip() == "":
        print("Сообщение не может быть пустым.")
        return

    mastodon = Mastodon(
        access_token="toot_usercred.secret",
        api_base_url="https://fosstodon.org",
    )

    try:
        status = mastodon.toot(message)
        print(f"Пост опубликован: {status['url']}")
    except Exception as e:
        print(f"Ошибка при публикации: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Опубликовать сообщение в Mastodon")
    parser.add_argument(
        "message",
        nargs="?",
        help="Сообщение для публикации в Mastodon",
        default="",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Выполнить процедуру OAuth аутентификации",
    )
    args = parser.parse_args()

    if args.auth:
        get_access_token_oauth()
    else:
        if not args.message or args.message.strip() == "":
            print("Ошибка: Необходимо указать сообщение для публикации.")
            print("Используйте --auth для первоначальной настройки.")
            parser.print_help()
            exit(1)
        publish_message(message=args.message)
