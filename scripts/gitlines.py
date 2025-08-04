#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "requests",
# ]
# ///
"""
Скрипт для анализа коммитов репозитория GitHub, отслеживания добавленных/удалённых строк
и количества файлов в каждом коммите с использованием GitHub API.

Использование:
    python gitlines.py <repo_url> <github_token>

Пример:
    uv run gitlines.py https://github.com/username/repo your_github_token
"""

import sys
import requests
import re
from datetime import datetime
from typing import Tuple, Dict, List, Optional


def parse_repo_info(repo_url: str) -> Tuple[str, str]:
    """Извлечь владельца и имя репозитория из URL GitHub."""
    pattern = r"github\.com/([^/]+)/([^/]+)"
    match = re.search(pattern, repo_url)

    if not match:
        raise ValueError(f"Некорректный URL репозитория GitHub: {repo_url}")

    return match.group(1), match.group(2)


def get_commits(owner: str, repo: str, token: str) -> List[Dict]:
    """Получить все коммиты из репозитория."""
    commits = []
    page = 1

    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        params = {"per_page": 100, "page": page}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        page_commits = response.json()
        if not page_commits:
            break

        commits.extend(page_commits)
        page += 1

    return commits


def get_commit_stats(owner: str, repo: str, sha: str, token: str) -> Dict:
    """Получить подробную статистику для конкретного коммита."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_file_count(owner: str, repo: str, sha: str, token: str) -> Optional[int]:
    """Получить количество файлов в репозитории на момент конкретного коммита."""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{sha}?recursive=1"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        # Считаем только blobs (файлы), не trees (папки)
        file_count = sum(1 for item in data.get("tree", []) if item["type"] == "blob")
        return file_count
    except requests.exceptions.RequestException:
        # Некоторые большие репозитории могут достичь лимита GitHub API на рекурсивное получение дерева
        return None


def main():
    if len(sys.argv) != 3:
        print(f"Использование: {sys.argv[0]} <repo_url> <github_token>")
        sys.exit(1)

    repo_url = sys.argv[1]
    token = sys.argv[2]

    try:
        owner, repo = parse_repo_info(repo_url)

        print(f"Анализ репозитория: {owner}/{repo}")

        commits = get_commits(owner, repo, token)
        print(f"Найдено коммитов: {len(commits)}. Анализ каждого коммита...")

        print("\nАнализ коммитов:")
        print("=" * 80)
        print(
            f"{'SHA':<10} {'Дата':<19} {'Добавлено':<8} {'Удалено':<8} {'Файлов':<7} {'Сообщение'}"
        )
        print("-" * 80)

        total_additions = total_deletions = 0

        for commit in commits:
            sha = commit["sha"]
            commit_data = get_commit_stats(owner, repo, sha, token)

            # Извлекаем статистику
            stats = commit_data.get("stats", {})
            additions = stats.get("additions", 0)
            total_additions += int(additions)
            deletions = stats.get("deletions", 0)
            total_deletions += int(deletions)

            # Получаем количество файлов
            file_count = get_file_count(owner, repo, sha, token)
            file_count_str = str(file_count) if file_count is not None else "N/A"

            # Форматируем дату
            date_str = commit_data["commit"]["author"]["date"]
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            formatted_date = date.strftime("%Y-%m-%d %H:%M:%S")

            # Получаем сообщение коммита (только первая строка)
            message = commit_data["commit"]["message"].split("\n")[0]

            print(
                f"{sha[:7]:<10} {formatted_date:<19} {additions:<8} {deletions:<8} {file_count_str:<7} {message[:40]}"
            )

        print("=" * 80)
        print(f"Всего добавлено строк: {total_additions}")
        print(f"Всего удалено строк: {total_deletions}")
        print(f"Чистое изменение...: {total_additions - total_deletions}")

    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
