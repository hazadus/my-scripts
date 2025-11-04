#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "requests",
# ]
# ///
"""
Демонстрирует использование uv для выполнения простейшего standalone скрипта.
"""
import requests

response = requests.get(
    "https://raw.githubusercontent.com/hazadus/readwise-links/refs/heads/main/links/tags/uv.md"
)
print(response.text)
