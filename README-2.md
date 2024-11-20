# Emoji Bot

## О боте

EMOJI BOT v1.1.2 (BETA 03)
ALL RIGHTS RESERVED

https://t.me/EmojiOfficial_bot

## Настройка и запуск

Потребуется Python 3.9 и [FFMPEG](https://ffmpeg.org/download.html).
Если у Вас MacOS:

Установите Homebrew.
    ```shell
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

Установите ffmpeg.
    ```shell
    brew install ffmpeg
    ```

1. Создайте бота с [BotFather](https://t.me/BotFather) и скопируйте токен.

2. Создайте `.env` файл. Вставьте туда ваш токен бота, или воспользуйтесь файлом `.env.example`, переименовав его в `.env`.

3. Установите зависимости из `requirements.txt`.
    ```shell
    pip install -r requirements.txt
    ```

4. Создайте базу данных в pgAdmin со следующими запросами:
    ```postgresql
    CREATE TABLE users (
        user_id BIGINT PRIMARY KEY,
        subscription_status BOOLEAN DEFAULT FALSE
    );

    CREATE TABLE sticker_packs (
        id SERIAL PRIMARY KEY, -- Уникальный идентификатор
        user_id BIGINT NOT NULL, -- ID пользователя
        pack_name VARCHAR(255) NOT NULL, -- Название пака
        short_name VARCHAR(64), -- Короткое название
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(), -- Дата и время создания
        set_type TEXT NOT NULL -- Тип набора (например, custom-emoji, text и т.д.)
    );
    ```

5. Измените данные подключения к базе данных на свои в настройках бд.

6. Запустите бота локально или создайте Dockerfile из списка зависимостей и запустите через Docker.