FROM python:3.12-slim

# В контейнере нет звуковой карты — отключаем звук SDL,
# чтобы pygame не падал при инициализации.
ENV SDL_AUDIODRIVER=dummy \
    SDL_VIDEODRIVER=x11 \
    PYTHONUNBUFFERED=1

# Шрифт DejaVu — нужен для корректного отображения кириллицы
# в интерфейсе игры (pygame ищет системные шрифты).
# X11/GL-библиотеки — требуются pygame на Linux (иначе import падает
# с ошибкой про libGL.so.1 и SDL не сможет открыть графическое окно).
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        libgl1 \
        libx11-6 \
        libxext6 \
        libxrandr2 \
        libxrender1 \
        libxi6 \
        libxcursor1 \
        libxinerama1 \
        libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Точка входа: одна команда запускает игру.
# Для графического окна в контейнере требуется X11 (см. README.md).
CMD ["python", "main.py"]
