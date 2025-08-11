# Сгенерировать сообщение коммита (см. https://github.com/hazadus/gh-commitmsg)
commitmsg:
    gh commitmsg --language russian --examples

# Отформатировать код
format:
    uvx black .
    uvx isort .