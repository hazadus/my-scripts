#!/usr/bin/env -S uv run --quiet --script

"""
Изменяет системную тему MacOS на светлую или темную.

Использование:
    theme.py dark
    theme.py light
"""
import argparse
import subprocess


def main():
    parser = argparse.ArgumentParser(
        description="Изменение системной темы на светлую или тёмную"
    )
    parser.add_argument(
        "mode", help="dark | light – тема на которую нужно переключиться"
    )
    args = parser.parse_args()

    change_theme(mode=args.mode)


def change_theme(mode: str) -> None:
    if mode not in ["dark", "light"]:
        print("Укажите параметр dark или light для переключения темы")
        return

    commands = {
        "dark": 'tell app "System Events" to tell appearance preferences to set dark mode to true',
        "light": 'tell app "System Events" to tell appearance preferences to set dark mode to false',
    }

    subprocess.run(
        [
            "osascript",
            "-e",
            commands[mode],
        ],
    )


if __name__ == "__main__":
    main()
