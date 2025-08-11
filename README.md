# `my-scritps` – утилиты на Python под `uv`

## Материалы по теме

- [Better alternative to shell scripts with Python, uv and pytest](https://hamatti.org/posts/better-alternative-to-shell-scripts-with-python-uv-and-pytest/)
- [Pesky little scripts](https://rednafi.com/misc/pesky_little_scripts/)

## `ytdlp.py`

### Требования

- `ffmpeg` for highest quality downloads (`brew install ffmpeg`)

```bash
# Скачать ссылку
uv run ytdlp.py "https://youtu.be/VGF8FAV1eeM?si=RU8FP4JHrsduOJCh"

# Скачать ссылку в высшем качестве (требуется ffmpeg)
uv run ytdlp.py -hq "https://youtu.be/VGF8FAV1eeM"

# Скачать ссылку из буфера
uv run ytdlp.py "$(pbpaste)"

# Скачать ссылку из буфера в высшем качестве
uv run ytdlp.py -hq "$(pbpaste)"

# Открыть папку с закачками в Finder
open "/Users/hazadus/Downloads/FromYouTube"
```
## `gitlines.py`

Скрипт для анализа коммитов репозитория GitHub, отслеживания добавленных/удалённых строк и количества файлов в каждом коммите с использованием GitHub API.

### Требования

- GitHub Token с правом чтения репозитория

```bash
# Анализ репозитория
uv run gitlines.py "https://github.com/username/repo" your_github_token
```

Выводит таблицу с SHA, датой, количеством добавленных/удалённых строк, количеством файлов и сообщением коммита. В конце — суммарная статистика.

## `ycs3.py`

Скрипт для загрузки файла в S3-совместимое хранилище Яндекс Облака.

### Требования

- Указать свои AWS_ACCESS_KEY и AWS_SECRET_KEY в скрипте
- Доступ к бакету Яндекс Облака

```bash
# Загрузить файл в S3
uv run ycs3.py /path/to/file
```

Файл будет загружен в бакет с именем, указанным в переменной AWS_BUCKET_NAME.

## `toot.py`

Скрипт для публикации сообщений в Mastodon с использованием Mastodon.py API.

### Требования

- Аккаунт на Mastodon (настроен для fosstodon.org)
- Первоначальная настройка OAuth (выполняется один раз)

### Первоначальная настройка

Для первого использования нужно выполнить OAuth аутентификацию:

```bash
# Выполнить процедуру OAuth аутентификации
uv run toot.py --auth
```

Скрипт автоматически зарегистрирует приложение и проведёт через процесс OAuth авторизации.

### Использование

```bash
# Опубликовать сообщение
uv run toot.py "Привет, Mastodon!"

# Опубликовать сообщение из буфера обмена
uv run toot.py "$(pbpaste)"

# Опубликовать многострочное сообщение
uv run toot.py "Первая строка
Вторая строка
Третья строка"

# Посмотреть справку по командам
uv run toot.py --help
```

## `rss.py`

Скрипт для работы с OPML файлами RSS лент. Позволяет просматривать структуру OPML файла и читать посты из всех лент за указанную дату.

### Требования

- OPML файл с RSS лентами (например, `feeds.opml`)

### Использование

```bash
# Показать структуру OPML файла
uv run rss.py scripts/feeds.opml

# Прочитать все посты за указанную дату (формат YYYY-MM-DD)
uv run rss.py --read 2025-08-11 scripts/feeds.opml

# Посмотреть справку по командам
uv run rss.py --help
```

Скрипт выводит посты в хронологическом порядке (от старых к новым) с заголовком, ссылкой, названием ленты и датой публикации.