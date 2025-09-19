#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "requests",
#   "pydantic",
# ]
# ///
"""
Скрипт для получения и вывода time entries из Toggl Track за указанный диапазон дат.

По умолчанию показывает данные за вчерашний день, если диапазон не указан.
API Key передается как обязательный параметр CLI.

Использование:
    uv run scripts/toggltrack.py <api_key>
    uv run scripts/toggltrack.py <api_key> --start-date 2025-09-18 --end-date 2025-09-19

Пример:
    uv run scripts/toggltrack.py api_key
    uv run scripts/toggltrack.py api_key --start-date 2025-09-18
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from pydantic import BaseModel


# MARK: Data Models
class UserInfo(BaseModel):
    """Модель для ответа /api/v9/me"""

    id: int
    api_token: str
    email: str
    fullname: str
    timezone: str
    default_workspace_id: int
    beginning_of_week: int
    image_url: str
    created_at: str
    updated_at: str


class Project(BaseModel):
    """Модель для проектов из /api/v9/workspaces/{workspace_id}/projects"""

    id: int
    workspace_id: int
    client_id: Optional[int]
    name: str
    is_private: bool
    active: bool
    color: str
    billable: bool
    client_name: Optional[str]
    can_track_time: bool


class TimeEntry(BaseModel):
    """Модель для time entries из /api/v9/me/time_entries"""

    id: int
    workspace_id: int
    project_id: Optional[int]
    task_id: Optional[int]
    billable: bool
    start: str
    stop: Optional[str]
    duration: int
    description: Optional[str]
    tags: List[str]
    tag_ids: List[int]
    duronly: bool
    at: str
    server_deleted_at: Optional[str]
    user_id: int
    uid: int
    wid: int
    pid: Optional[int]


# MARK: main()
def main():
    """Основная функция скрипта"""
    try:
        # Парсинг аргументов
        args = parse_arguments()

        # Определяем диапазон дат
        if args.start_date and args.end_date:
            start_date = args.start_date
            end_date = args.end_date
        elif args.start_date:
            # Если указана только начальная дата, берем один день
            start_date = args.start_date
            end_date = args.start_date
        else:
            # По умолчанию вчерашний день
            start_date, end_date = get_default_date_range()

        print(f"Получение time entries за период: {start_date} - {end_date}")

        # Получение информации о пользователе
        user_info = get_user_info(args.api_key)
        workspace_id = user_info.default_workspace_id

        # Получение проектов
        projects = get_projects(args.api_key, workspace_id)

        # Получение time entries
        time_entries = get_time_entries(args.api_key, start_date, end_date)

        if not time_entries:
            print("\nНе найдено time entries за указанный период.")
            return

        # Группировка и вывод отчета
        grouped_entries = group_time_entries_by_date_and_project(time_entries, projects)
        print_time_entries_report(grouped_entries, projects)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Ошибка: Неверный API ключ. Проверьте правильность ключа.")
        elif e.response.status_code == 403:
            print("Ошибка: Доступ запрещен. Проверьте права доступа API ключа.")
        else:
            print(f"Ошибка HTTP {e.response.status_code}: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        sys.exit(1)


# MARK: Helper functions
def get_user_info(api_key: str) -> UserInfo:
    """Получить информацию о пользователе из /api/v9/me"""
    url = "https://api.track.toggl.com/api/v9/me"
    response = requests.get(url, auth=(api_key, "api_token"))
    response.raise_for_status()
    return UserInfo(**response.json())


def get_projects(api_key: str, workspace_id: int) -> List[Project]:
    """Получить проекты из /api/v9/workspaces/{workspace_id}/projects"""
    url = f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects"
    response = requests.get(url, auth=(api_key, "api_token"))
    response.raise_for_status()
    return [Project(**project_data) for project_data in response.json()]


def get_time_entries(api_key: str, start_date: str, end_date: str) -> List[TimeEntry]:
    """Получить time entries из /api/v9/me/time_entries за указанный период"""
    url = "https://api.track.toggl.com/api/v9/me/time_entries"
    params = {"start_date": start_date, "end_date": end_date}
    response = requests.get(url, params=params, auth=(api_key, "api_token"))
    response.raise_for_status()
    return [TimeEntry(**entry_data) for entry_data in response.json()]


def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Получение time entries из Toggl Track за указанный период"
    )

    parser.add_argument("api_key", help="API ключ для доступа к Toggl Track API")

    parser.add_argument(
        "--start-date", help="Начальная дата в формате YYYY-MM-DD (по умолчанию: вчера)"
    )

    parser.add_argument(
        "--end-date", help="Конечная дата в формате YYYY-MM-DD (по умолчанию: сегодня)"
    )

    return parser.parse_args()


def get_default_date_range():
    """Получить диапазон дат по умолчанию (от вчера до сегодня)"""
    yesterday = datetime.now() - timedelta(days=1)
    today = datetime.now()
    start_date = yesterday.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    return start_date, end_date


def format_duration(seconds: int) -> str:
    """Преобразовать секунды в формат HH:MM"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def format_date_from_iso(iso_string: str) -> str:
    """Извлечь дату из ISO строки в формате YYYY-MM-DD"""
    return iso_string[:10]


def group_time_entries_by_date_and_project(
    time_entries: List[TimeEntry], projects: List[Project]
) -> Dict[str, Dict[int, Dict[str, int]]]:
    """Группировка time entries по датам, проектам и описанию с суммированием времени"""
    grouped = {}

    for entry in time_entries:
        date = format_date_from_iso(entry.start)
        project_id = entry.project_id or 0  # 0 для entries без проекта
        description = entry.description or "Без описания"

        if date not in grouped:
            grouped[date] = {}

        if project_id not in grouped[date]:
            grouped[date][project_id] = {}

        if description not in grouped[date][project_id]:
            grouped[date][project_id][description] = 0

        grouped[date][project_id][description] += entry.duration

    return grouped


def print_time_entries_report(
    grouped_entries: Dict[str, Dict[int, Dict[str, int]]], projects: List[Project]
):
    """Вывод отчета о time entries в заданном формате"""
    # Создаем словарь проектов для быстрого поиска
    projects_dict = {project.id: project for project in projects}

    # Сортируем даты
    for date in sorted(grouped_entries.keys()):
        # Вычисляем суммарное время за день
        daily_total = 0
        for project_id, project_entries in grouped_entries[date].items():
            for description, duration in project_entries.items():
                daily_total += duration

        daily_total_str = format_duration(daily_total)
        print(f"\n## {date} (Всего: {daily_total_str})")

        # Сортируем проекты по ID
        for project_id in sorted(grouped_entries[date].keys()):
            project_entries = grouped_entries[date][project_id]

            # Получаем информацию о проекте
            if project_id == 0:
                project_name = "Без проекта"
                client_name = None
            else:
                project = projects_dict.get(project_id)
                if project:
                    project_name = project.name
                    client_name = project.client_name
                else:
                    project_name = f"Проект {project_id}"
                    client_name = None

            # Формируем заголовок проекта
            if client_name:
                print(f"\n### {project_name} ({client_name})")
            else:
                print(f"\n### {project_name}")

            # Выводим каждое уникальное описание с суммарным временем
            for description in sorted(project_entries.keys()):
                total_duration = project_entries[description]
                duration_str = format_duration(total_duration)
                print(f"- {description} - {duration_str}")


# MARK: Main entry point
if __name__ == "__main__":
    main()
