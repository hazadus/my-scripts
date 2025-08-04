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