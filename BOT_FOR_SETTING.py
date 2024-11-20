# EMOJI BOT v1.1.2 (BETA 03)

# ADDITIONAL:
# Bot name is attached to all the pack titles
# Checking subscription on all the channels in array when: EVERY HANDLER IS CALLED (COMMENTED)

# --------------------------- ЗАВИСИМОСТИ --------------------------- #

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, InputMediaPhoto, InputMediaVideo
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
import asyncio
import os
import requests
import re
import uuid
import subprocess
import asyncpg
import logging

# ----------------------- НАСТРОЙКА БОТА И БД ----------------------- #

# Настройка логирования
logging.basicConfig(level=logging.INFO)

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{API_TOKEN}'
TELEGRAM_FILE_URL = f"https://api.telegram.org/file/bot{API_TOKEN}"
FFMPEG_PATH = 'ffmpeg'  # Убедитесь, что ffmpeg установлен и доступен в PATH

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определяем состояния
class StickerPackForm(StatesGroup):
    waiting_for_pack_name = State()
    waiting_for_short_name = State()
    waiting_for_sticker = State()
    waiting_for_pack_selection = State()
    waiting_for_sticker_action = State()
    adding_sticker = State()
    removing_sticker = State()
    set_thumbnail = State()
    renaming_pack = State()
    confirming_deletion = State()
    converting_stickers = State()

class EmojiPackForm(StatesGroup):
    waiting_for_pack_name = State()
    waiting_for_short_name = State()
    waiting_for_sticker = State()
    waiting_for_pack_selection = State()
    waiting_for_sticker_action = State()
    adding_sticker = State()
    deleting_emoji = State()
    renaming_pack = State()
    confirming_deletion = State()

class CloneStickerPackStates(StatesGroup):
    waiting_for_stickerpack_link = State()
    waiting_for_new_pack_name = State()
    waiting_for_new_pack_title = State()
    selecting_existing_pack = State()

class CloneEmojiPackStates(StatesGroup):
    waiting_for_pack_link = State()
    waiting_for_pack_name = State()
    waiting_for_short_name = State()
    waiting_for_sticker = State()

class SubscriptionState(StatesGroup):
    checking_subscription = State()

async def create_db_pool():
    return await asyncpg.create_pool(
        user='ВАШ_ЮЗЕР', # Если по умолчанию, то postgres ставьте
        password='ВАШ_ПАРОЛЬ',
        database='НАЗВАНИЕ_БД',
        host='localhost'
    )

db_pool = None

# Список каналов, на которые необходимо подписаться
CHANNELS = [
    "@wholeshoes"
]

# Словарь для хранения файлов медиа-группы и таймеров по их media_group_id
media_group_storage = {}
media_group_timers = {}
media_group_processing_messages = {}

# Время ожидания в секундах перед обработкой медиа-группы
WAIT_TIME = 2

# Кнопка для проверки подписки
check_subscription_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Проверить подписку", callback_data="check_subscription")]
    ]
)

# Кнопки для выбора дальнейших действий после успешной проверки подписки
main_menu_buttons = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Создать ✨ премиум эмодзи", callback_data="create_emojipack")],
        [InlineKeyboardButton(text="🌄 Создать стикерпак", callback_data="create_stickerpack")],
        [InlineKeyboardButton(text="🔄 Преобразовать стикеры и эмодзи", callback_data="clone")],
        [InlineKeyboardButton(text="📂 Список моих паков", callback_data="list")]
    ]
)

# Функция для создания меню команд
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="/menu", description="🏠 Открыть меню"),
        BotCommand(command="/add", description="➕ Добавить стикер"),
        BotCommand(command="/list", description="☰ Список стикеров"),
        BotCommand(command="/clone", description="∞ Копировать пак"),
        BotCommand(command="/delete", description="✖ Удалить стикер"),
        BotCommand(command="/help", description="❓ Помощь"),
        BotCommand(command="/language", description="🌐 Сменить язык")
    ]
    await bot.set_my_commands(commands)


# ------------------------ ПРОВЕРКА ПОДПИСКИ ------------------------- #

# # Функция для проверки подписки
# async def is_user_subscribed(user_id):
#     for channel in CHANNELS:
#         member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
#         if member.status not in ["member", "administrator", "creator"]:
#             return False
#     return True

# class SubscriptionMiddleware(BaseMiddleware):
#     async def __call__(self, handler, event, data):
#         logging.info("Middleware вызывается!")  # Лог для проверки вызова Middleware

#         global db_pool
#         state: FSMContext = data['state']
#         user_id = None

#         # Определяем user_id только для событий с from_user
#         if isinstance(event, (types.Message, types.CallbackQuery)):
#             user_id = event.from_user.id
#             logging.info(f"Проверка пользователя с ID: {user_id}")  # Лог для проверки user_id

#         if user_id:
#             # Проверяем пользователя в базе данных
#             async with db_pool.acquire() as connection:
#                 user = await connection.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
#                 logging.info(f"Данные пользователя из БД: {user}")

#                 if user:
#                     # Проверяем подписку
#                     if await is_user_subscribed(user_id):
#                         logging.info("Подписка подтверждена")
#                         await connection.execute('UPDATE users SET subscription_status = TRUE WHERE user_id = $1', user_id)
#                         await state.clear()
#                         return await handler(event, data)
#                     else:
#                         logging.info("Подписка НЕ подтверждена")
#                         await connection.execute('UPDATE users SET subscription_status = FALSE WHERE user_id = $1', user_id)
#                         # Отправляем сообщение о необходимости подписки
#                         channels_list = "\n".join([f"- {channel}" for channel in CHANNELS])
#                         if isinstance(event, types.Message):
#                             await event.answer(
#                                 f"Пожалуйста, подпишитесь на следующие каналы для использования функций бота:\n{channels_list}\n"
#                                 f"После подписки нажмите кнопку ниже для проверки.",
#                                 reply_markup=check_subscription_button
#                             )
#                         elif isinstance(event, types.CallbackQuery):
#                             await event.message.answer(
#                                 f"Пожалуйста, подпишитесь на следующие каналы для использования функций бота:\n{channels_list}\n"
#                                 f"После подписки нажмите кнопку ниже для проверки.",
#                                 reply_markup=check_subscription_button
#                             )
#                         await state.set_state(SubscriptionState.checking_subscription)
#                         return


#         # Если событие не обрабатывается или user_id не найден, продолжаем выполнение
#         return await handler(event, data)

# # Добавляем Middleware
# dp.update.middleware(SubscriptionMiddleware())

# ---------------------- АКТУАЛИЗАЦИЯ ДАННЫХ ------------------------ #
# ---------------------------- ХЕНДЛЕРЫ ----------------------------- #

@dp.callback_query(lambda c: c.data == "list")
async def handle_my_stickers(callback_query: types.CallbackQuery, state: FSMContext):
    await my_stickers(callback_query, state)

@dp.callback_query(lambda c: c.data == "show_emoji_packs")
async def handle_show_emoji_packs(callback_query: types.CallbackQuery, state: FSMContext):
    await show_emoji_packs(callback_query, state)

@dp.callback_query(lambda c: c.data == "show_regular_packs")
async def handle_show_regular_packs(callback_query: types.CallbackQuery, state: FSMContext):
    await show_regular_packs(callback_query, state)

@dp.callback_query(lambda c: c.data == "menu")
async def handle_show_menu(callback_query: types.CallbackQuery):
    # Используем тот же ответ, что и в команде /menu
    await menu_command(callback_query.message)
    await callback_query.answer()  # Закрываем уведомление

@dp.callback_query(lambda c: c.data == "remove_sticker")
async def start_removing_sticker(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные о выбранном стикерпаке из состояния
    data = await state.get_data()
    pack_name = data.get('pack_name')
    short_name = data.get('short_name')

    if not short_name or not pack_name:
        await callback_query.answer("Ошибка: стикер-пак не выбран.", show_alert=True)
        return

    # Ссылка на стикерпак
    pack_link = f"https://t.me/addstickers/{short_name}"

    # Создаём клавиатуру с кнопкой "Отмена"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
    ])

    # Формируем сообщение с информацией о наборе
    response_message = (
        f"Удаление стикеров из набора [{pack_name}]({pack_link})\n\n"
        "Пришлите стикер из этого набора, который хотите удалить."
    )

    # Отправляем сообщение с кнопкой "Отмена"
    await callback_query.message.edit_text(response_message, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(StickerPackForm.removing_sticker)
    await callback_query.answer()  # Закрываем уведомление

# Обработчик для начала переименования стикерпака
@dp.callback_query(lambda c: c.data == "rename_pack")
async def start_rename_pack(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные о выбранном стикерпаке из состояния
    data = await state.get_data()
    pack_name = data.get('pack_name')
    short_name = data.get('short_name')

    if not short_name or not pack_name:
        await callback_query.answer("Ошибка: стикер-пак не выбран.", show_alert=True)
        return

    # Ссылка на стикерпак
    pack_link = f"https://t.me/addstickers/{short_name}"

    # Создаём клавиатуру с кнопкой "Отмена"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
    ])

    # Формируем сообщение с информацией о паке
    response_message = (
        f"Переименование набора [{pack_name[:-18]}]({pack_link})\n\n"
        "Пришлите новое название"
    )

    # Отправляем сообщение с кнопкой "Отмена"
    await callback_query.message.edit_text(response_message, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(StickerPackForm.renaming_pack)
    await callback_query.answer()  # Закрываем уведомление

# Обработчик для начала переименования эмодзипака
@dp.callback_query(lambda c: c.data == "rename_emoji_pack")
async def start_rename_pack(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные о выбранном эмодзипаке из состояния
    data = await state.get_data()
    pack_name = data.get('pack_name')
    short_name = data.get('short_name')

    if not short_name or not pack_name:
        await callback_query.answer("Ошибка: эмодзипак не выбран.", show_alert=True)
        return

    # Ссылка на эмодзипак
    pack_link = f"https://t.me/addemoji/{short_name}"

    # Создаем клавиатуру с кнопкой "Отмена"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
    ])

    # Формируем сообщение с информацией о паке
    response_message = (
        f"Переименование набора [{pack_name[:-16]}]({pack_link})\n\n"
        "Пришлите новое название"
    )

    # Отправляем сообщение с кнопкой "Отмена"
    await callback_query.message.edit_text(response_message, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(EmojiPackForm.renaming_pack)
    await callback_query.answer()  # Закрываем уведомление

# -------------------------- КОМАНДЫ/МЕНЮ --------------------------- #

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    global db_pool
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

    # Подключаемся к базе данных и проверяем, есть ли пользователь
    async with db_pool.acquire() as connection:
        user = await connection.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
        if not user:
            # Если пользователя нет, добавляем его в базу данных с subscription_status = False
            await connection.execute('INSERT INTO users (user_id, subscription_status) VALUES ($1, $2)', user_id, False)

    await message.answer(
        f"*Привет, {user_name}*\n\n"
        "С помощью этого бота можно создать свои 🌟 *Премиум эмодзи* и Стикеры из изображений, видео и GIF\\!\n"
        "А также можно собрать свои любимые эмодзи\\/стикеры в один набор\\!\n"
        "Ещё бот умеет конвертировать обычные стикерпаки в премиум\\-эмодзи\\.\n\n"
        "Команда /help \\- посмотреть доступные команды",
        parse_mode="MarkdownV2",
        reply_markup=main_menu_buttons
    )

# ЭТОТ СТАРТ С ПОДТВЕРЖДЕНИЕМ ПОДПИСКИ
# @dp.message(Command("start"))
# async def start_command(message: types.Message, state: FSMContext):
#     global db_pool
#     user_id = message.from_user.id
#     user_name = message.from_user.first_name or "User"

#     # Подключаемся к базе данных и проверяем, есть ли пользователь
#     async with db_pool.acquire() as connection:
#         user = await connection.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
#         if not user:
#             # Если пользователя нет, добавляем его в базу данных с subscription_status = False
#             await connection.execute('INSERT INTO users (user_id, subscription_status) VALUES ($1, $2)', user_id, False)

#     # Проверяем статус подписки
#     if user and user['subscription_status']:
#         # Если подписка активна, показываем главное меню
#         await message.answer(
#             f"*Привет, {user_name}*\n\n"
#             "С помощью этого бота можно создать свои 🌟 *Премиум эмодзи* и Стикеры из изображений, видео и GIF\\!\n"
#             "А также можно собрать свои любимые эмодзи\\/стикеры в один набор\\!\n"
#             "Ещё бот умеет конвертировать обычные стикерпаки в премиум\\-эмодзи\\.\n\n"
#             "Команда /help \\- посмотреть доступные команды",
#             parse_mode="MarkdownV2",
#             reply_markup=main_menu_buttons
#         )
#         await state.clear()
#     else:
#         # Если подписка не подтверждена, перенаправляем на проверку подписки
#         channels_list = "\n".join([f"- {channel}" for channel in CHANNELS])
#         await message.answer(
#             f"Добро пожаловать! Пожалуйста, подпишитесь на следующие каналы для использования функций бота:\n{channels_list}\n"
#             f"После подписки нажмите кнопку ниже для проверки.",
#             reply_markup=check_subscription_button
#         )
#         await state.set_state(SubscriptionState.checking_subscription)

# @dp.callback_query(lambda callback_query: callback_query.data == "check_subscription", StateFilter(SubscriptionState.checking_subscription))
# async def check_subscription_handler(callback_query: types.CallbackQuery, state: FSMContext):
#     global db_pool
#     user_id = callback_query.from_user.id
#     user_name = message.from_user.first_name or "User"

#     # Здесь выполняется проверка подписки пользователя на каналы
#     is_subscribed = True  # Эта переменная должна быть результатом вашей проверки подписки

#     # Логика проверки подписки (примерный шаблон)
#     for channel in CHANNELS:
#         member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
#         if member.status not in ["member", "administrator", "creator"]:
#             is_subscribed = False
#             break

#     async with db_pool.acquire() as connection:
#         if is_subscribed:
#             # Если пользователь подписан на все каналы, обновляем статус в базе данных
#             await connection.execute('UPDATE users SET subscription_status = TRUE WHERE user_id = $1', user_id)
#             await callback_query.message.answer(
#                 f"*Привет, {user_name}*\n\n"
#                 "С помощью этого бота можно создать свои 🌟 *Премиум эмодзи* и Стикеры из изображений, видео и GIF\\!\n"
#                 "А также можно собрать свои любимые эмодзи\\/стикеры в один набор\\!\n"
#                 "Ещё бот умеет конвертировать обычные стикерпаки в премиум\\-эмодзи\\.\n\n"
#                 "Команда /help \\- посмотреть доступные команды",
#                 parse_mode="MarkdownV2",
#                 reply_markup=main_menu_buttons
#             )
#             await state.clear()
#         else:
#             # Если пользователь не подписан, отправляем сообщение
#             await callback_query.message.answer(
#                 "Вы не подписаны на все каналы. Пожалуйста, убедитесь, что вы подписались на все каналы и попробуйте снова.",
#                 reply_markup=check_subscription_button
#             )

#     # Уведомляем Telegram, что callback обработан
#     await callback_query.answer()

@dp.message(Command("menu"))
@dp.message(Command("clone"))
@dp.message(Command("menu"))
async def menu_command(message: types.Message):
    user_name = message.from_user.first_name or "User"
    await message.answer(
        f"*Привет, {user_name}*\n\n"
        "С помощью этого бота можно создать свои 🌟 *Премиум эмодзи* и Стикеры из изображений, видео и GIF\\!\n"
        "А также можно собрать свои любимые эмодзи\\/стикеры в один набор\\!\n"
        "Ещё бот умеет конвертировать обычные стикерпаки в премиум\\-эмодзи\\.\n\n"
        "⚡ Наши каналы: @EMOJI\\_official \\- эмодзи, @STIKERS\\_official \\- стикеры\n\n"
        "Команда /help \\- посмотреть доступные команды",
        parse_mode="MarkdownV2",
        reply_markup=main_menu_buttons
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "⚡ Наши каналы: @EMOJI\\_official \\- эмодзи, @STIKERS\\_official \\- стикеры\n\n"
        "*Доступные команды:*\n\n"
        "🏠 /menu \\- Открыть меню\n"
        "➕ /add \\- Добавить стикер\n"
        "☰ /list \\- Список стикеров\n"
        "∞ /clone \\- Копировать пак\n"
        "✖ /delete \\- Удалить стикер\n"
        "❓ /help \\- Помощь\n"
        "🌐 /language \\- Сменить язык\n\n"
        "*Дополнительные команды:*\n"
        "🆕 /new \\- Создать новый пак\n"
        "✏️ /rename \\- Переименовать набор\n"
        "🗑️ /delpack \\- Удалить весь стикерпак\n\n",
        parse_mode="MarkdownV2"
    )

@dp.message(Command("list"))
@dp.message(Command("add"))
@dp.message(Command("delete"))
@dp.message(Command("delpack"))
@dp.message(Command("rename"))
async def my_stickers(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Извлечение информации о стикерпаках и эмодзипаках пользователя из базы данных
    async with db_pool.acquire() as connection:
        regular_packs = await connection.fetch(
            "SELECT id, pack_name, short_name FROM sticker_packs WHERE user_id = $1 AND set_type = 'regular'",
            user_id
        )
        emoji_packs = await connection.fetch(
            "SELECT id, pack_name, short_name FROM sticker_packs WHERE user_id = $1 AND set_type = 'custom_emoji'",
            user_id
        )

    # Сохраняем данные о паках в состояние
    await state.update_data(regular_packs=regular_packs, emoji_packs=emoji_packs)

    # Показываем меню с эмодзипаками по умолчанию
    await show_emoji_packs(message, state)

# Функция для отображения меню взаимодействия с эмодзипаками
async def show_emoji_packs(message_or_query, state: FSMContext):
    data = await state.get_data()
    emoji_packs = data.get('emoji_packs', [])

    # Создаем кнопки для переключения между эмодзи и стикерами
    switch_buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Премиум эмодзи", callback_data="show_emoji_packs"),
                InlineKeyboardButton(text="🖼 Стикеры", callback_data="show_regular_packs")
            ]
        ]
    )

    # Создаем кнопки для взаимодействия с каждым эмодзипаком
    emoji_pack_buttons = [
        [InlineKeyboardButton(text=f"🌟 {pack['pack_name'][:-16]}", callback_data=f"emoji_pack_{pack['id']}")]
        for pack in emoji_packs
    ]

    # Кнопки для создания нового эмодзипака и других действий
    interaction_buttons = [
        [InlineKeyboardButton(text="➕ Создать новый 🌟 Премиум эмодзи-пак", callback_data="create_emojipack")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    ]

    # Формируем полную клавиатуру
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=switch_buttons.inline_keyboard + emoji_pack_buttons + interaction_buttons
    )

    # Формируем сообщение с количеством эмодзипаков
    response_message = (
        "Список Ваших созданных эмодзи паков:\n\n"
        f"У Вас {len(emoji_packs)} премиум эмодзи паков\n\n"
        "👇 Выберите пак, с которым хотите взаимодействовать"
    )

    # Проверяем, является ли вызов из callback_query
    if isinstance(message_or_query, types.CallbackQuery):
        await message_or_query.message.edit_text(response_message, reply_markup=keyboard)
        await message_or_query.answer()  # Закрываем уведомление
    else:
        # Если вызов из сообщения
        await message_or_query.answer(response_message, reply_markup=keyboard)

# Функция для отображения меню взаимодействия со стикерпаками
async def show_regular_packs(message_or_query, state: FSMContext):
    data = await state.get_data()
    regular_packs = data.get('regular_packs', [])

    # Создаем кнопки для переключения между эмодзи и стикерами
    switch_buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌟 Премиум эмодзи", callback_data="show_emoji_packs"),
                InlineKeyboardButton(text="✅ Стикеры", callback_data="show_regular_packs")
            ]
        ]
    )

    # Создаем кнопки для взаимодействия с каждым стикерпаком
    regular_pack_buttons = [
        [InlineKeyboardButton(text=f"{pack['pack_name'][:-18]}", callback_data=f"pack_{pack['id']}")]
        for pack in regular_packs
    ]

    # Кнопки для создания нового стикерпака и других действий
    interaction_buttons = [
        [InlineKeyboardButton(text="➕ Создать новый 🖼 Стикер-пак", callback_data="create_stickerpack")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    ]

    # Формируем полную клавиатуру
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=switch_buttons.inline_keyboard + regular_pack_buttons + interaction_buttons
    )

    # Формируем сообщение с количеством стикерпаков
    response_message = (
        "Список Ваших созданных стикер паков:\n\n"
        f"У Вас {len(regular_packs)} стикер пака\n\n"
        "👇 Выберите пак, с которым хотите взаимодействовать"
    )

    # Если вызов из callback_query, обновляем сообщение
    if isinstance(message_or_query, types.CallbackQuery):
        await message_or_query.message.edit_text(response_message, reply_markup=keyboard)
        await message_or_query.answer()  # Закрываем уведомление
    else:
        # Если вызов из сообщения
        await message_or_query.answer(response_message, reply_markup=keyboard)

# Начало добавления стикера в пак
@dp.callback_query(lambda c: c.data == "create_stickerpack")
async def add_sticker(callback_query: types.CallbackQuery, state: FSMContext):
    # Создаем клавиатуру с кнопкой "Отмена"
    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
        ]
    )

    # Формируем сообщение с инструкцией
    response_message = (
        "*Создание нового пака*\n\n"
        "✅ Выбран тип пака: стикер-пак\n\n"
        "✏️ Теперь введите *название* для нового пака"
    )

    # Отправляем сообщение с клавиатурой
    await callback_query.message.edit_text(response_message, reply_markup=cancel_keyboard, parse_mode="Markdown")

    # Устанавливаем состояние ожидания ввода названия пака
    await state.set_state(StickerPackForm.waiting_for_pack_name)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "create_emojipack")
async def add_emoji(callback_query: types.CallbackQuery, state: FSMContext):
    # Создание клавиатуры с кнопкой "Отмена"
    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
        ]
    )

    # Формируем сообщение
    response_message = (
        "*Создание нового пака*\n\n"
        "✅ *Выбран тип пака: премиум эмодзи-пак*\n\n"
        "✏️ Теперь введите *название* для нового пака"
    )

    # Отправляем сообщение
    await callback_query.message.edit_text(response_message, reply_markup=cancel_keyboard, parse_mode="Markdown")
    
    # Устанавливаем состояние ожидания имени пака
    await state.set_state(EmojiPackForm.waiting_for_pack_name)
    await callback_query.answer()

# Клонировать стикерпак
@dp.message(Command("clone_stickerpack"))
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Привет! Отправьте ссылку на стикерпак, который вы хотите клонировать.")
    await state.set_state(CloneStickerPackStates.waiting_for_stickerpack_link)

# Клонировать эмодзи
@dp.message(Command("clone_emojipack"))
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Отправьте ссылку на эмодзипак, который вы хотите клонировать.")
    await state.set_state(EmojiPackForm.waiting_for_pack_link)

# -------------------------- КЛОНИРОВАНИЕ -------------------------- #

@dp.callback_query(lambda c: c.data == "clone")
async def start_convert_stickers(callback_query: types.CallbackQuery, state: FSMContext):
    # Создаем клавиатуру с кнопкой "Отмена"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
    ])

    # Формируем сообщение с инструкцией
    response_message = (
        "С помощью этой команды можно конвертировать стикеры в премиум-эмодзи, "
        "а также создавать копию стикеров.\n\n"
        "Отправьте мне ссылку на набор стикеров или эмодзи, который хотите конвертировать или скопировать."
    )

    # Отправляем сообщение с инструкцией и кнопкой "Отмена"
    await callback_query.message.edit_text(response_message, reply_markup=keyboard)
    await state.set_state(StickerPackForm.converting_stickers)
    await callback_query.answer()  # Закрываем уведомление

@dp.message(StateFilter(StickerPackForm.converting_stickers))
async def handle_pack_link(message: types.Message, state: FSMContext):
    pack_link = message.text.strip()

    # Определяем тип пака по ссылке
    if "t.me/addemoji" in pack_link:
        pack_type = "emoji"
        short_name = pack_link.split("addemoji/")[-1]
    elif "t.me/addstickers" in pack_link:
        pack_type = "sticker"
        short_name = pack_link.split("addstickers/")[-1]
    else:
        await message.reply("Неверная ссылка. Пожалуйста, отправьте корректную ссылку на набор стикеров или эмодзи.")
        return

    # Сохраняем информацию в состояние
    await state.update_data(pack_link=pack_link, pack_type=pack_type, short_name=short_name)

    # Создаем меню с вариантами преобразования
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Стикер-пак", callback_data="convert_to_sticker_pack")],
        [InlineKeyboardButton(text="🌟 Премиум эмодзи-пак", callback_data="convert_to_emoji_pack")],
        [InlineKeyboardButton(text="➕ Добавить к существующему паку", callback_data="list")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    ])

    # Отправляем сообщение с меню
    await message.reply(
        f"Копирование пака {short_name}\n\nВыберите тип нового пака кнопкой ниже",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data in ["convert_to_sticker_pack", "convert_to_emoji_pack"])
async def start_convert(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные о паке из состояния
    data = await state.get_data()
    pack_type = data.get("pack_type")
    pack_name = data.get("pack_name")
    short_name = data.get("short_name")
    original_pack_link = data.get("pack_link")

    # Определяем тип нового пака в зависимости от нажатой кнопки
    new_pack_type = "sticker" if callback_query.data == "convert_to_sticker_pack" else "custom_emoji"

    # Сохраняем новый тип пака в состоянии
    await state.update_data(new_pack_type=new_pack_type)

    # Формируем сообщение с выделением текста жирным
    response_message = (
        "✅ *Ссылка сохранена!*\n\n"
        "Теперь придумайте короткую ссылку на пак\n"
        "(только *английские буквы* и *цифры*, без пробела)\n\n"
        "*Пример*: `link123`"
    )

    # Переход к следующему шагу
    await callback_query.message.edit_text(
        response_message,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]]
        ),
        parse_mode="Markdown"
    )
    await state.set_state(CloneStickerPackStates.waiting_for_new_pack_name)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "add_to_existing_pack")
async def add_to_existing_pack(callback_query: types.CallbackQuery, state: FSMContext):
    # Отправляем пользователя к списку доступных паков
    await callback_query.message.edit_text(
        "Выберите существующий пак из списка:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
        ])
    )
    # Здесь можно добавить логику для отображения списка паков
    await state.set_state(CloneStickerPackStates.selecting_existing_pack)
    await callback_query.answer()  # Закрываем уведомление

@dp.message(StateFilter(CloneStickerPackStates.waiting_for_new_pack_name))
async def process_short_name(message: types.Message, state: FSMContext):
    short_name = message.text.lower()

    # Проверяем, что имя состоит только из латинских букв, цифр и символов подчеркивания
    if not re.match(r'^[a-z][a-z0-9_]*$', short_name) or short_name == 'генерировать':
        response_message = (
            "❌ *К сожалению, это некорректная ссылка.*\n"
            "Ссылка может содержать только _английские буквы_, _цифры_ и _нижнее подчёркивание_, "
            "и не должна начинаться с цифры.\n\n"
            "Отправьте другую ссылку."
        )
        await message.reply(response_message, parse_mode="Markdown")
        return

    # Генерация имени пользователя
    user_data = await state.get_data()
    username = re.sub(r'[^a-zA-Z0-9_]', '', message.from_user.username or message.from_user.first_name).lower()
    if not username:
        username = 'user'

    # Генерация имени бота
    bot_info = await bot.get_me()
    bot_name = re.sub(r'[^a-zA-Z0-9_]', '', bot_info.username).lower()

    if short_name == 'генерировать':
        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
        short_name = f"{username}_pack_{unique_id}_by_{bot_name}".lower()
    else:
        short_name = f"{short_name}_by_{bot_name}"

    # Ограничиваем длину имени стикерпакета до 64 символов
    short_name = short_name[:64]

    await state.update_data(new_short_name=short_name)

        # Сообщение об успешной проверке
    response_message = (
        "✅ *Ссылка сохранена!*\n\n"
        "✏️ Теперь введите *название* для нового пака"
    )

    # Создание клавиатуры с кнопкой "Отмена"
    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
        ]
    )
    await message.reply(response_message, reply_markup=cancel_keyboard, parse_mode="Markdown")
    await state.set_state(CloneStickerPackStates.waiting_for_new_pack_title)

def process_video_for_sticker(input_path: str, output_path: str):
    """Процесс обработки видео для стикерпаков (размер 512x512)"""
    command = [
        FFMPEG_PATH,
        "-i", input_path,
        "-vf", (
            "scale=512:512:force_original_aspect_ratio=decrease,"
            "pad=512:512:(ow-iw)/2:(oh-ih)/2,"
            "format=rgba,"
            "chromakey=black:0.1:0.0"
        ),
        "-c:v", "libvpx-vp9",
        "-b:v", "512k",
        "-r", "30",
        "-an",
        "-t", "3",
        "-loop", "0",
        output_path
    ]
    subprocess.run(command, check=True)

def process_video_for_emoji(input_path: str, output_path: str):
    """Процесс обработки видео для эмодзипаков (размер 100x100)"""
    command = [
        FFMPEG_PATH,
        "-i", input_path,
        "-vf", (
            "scale=100:100:force_original_aspect_ratio=decrease,"
            "pad=100:100:(ow-iw)/2:(oh-ih)/2:color=0x00000000,"
            "colorkey=0x000000:0.3:0.1"
        ),
        "-c:v", "libvpx-vp9",
        "-b:v", "256k",
        "-r", "30",
        "-an",
        "-pix_fmt", "yuva420p",
        "-t", "3",
        output_path
    ]
    subprocess.run(command, check=True)

@dp.message(StateFilter(CloneStickerPackStates.waiting_for_new_pack_title))
async def create_new_pack(message: types.Message, state: FSMContext):
    pack_name = message.text.strip() + " @STIKER_official"
    data = await state.get_data()
    user_id = message.from_user.id
    short_name = data.get("new_short_name")
    original_short_name = data.get("short_name")
    new_pack_type = data.get("new_pack_type")
    set_type = ""

    if new_pack_type == "sticker":
        set_type = "regular"
    else:
        set_type = "custom_emoji"

    processing_message = await bot.send_message(chat_id=message.chat.id, text='⏳')

    try:
        response = requests.get(f"{TELEGRAM_API_URL}/getStickerSet", params={"name": original_short_name})
        sticker_set = response.json()

        if not sticker_set.get("ok"):
            await message.reply("Ошибка при получении информации о наборе.")
            return

        stickers = sticker_set["result"]["stickers"]

        # Обработка первого стикера/эмодзи
        first_sticker = stickers[0]
        is_animated = first_sticker.get("is_animated", False)
        is_video = first_sticker.get("is_video", False)
        file_id = first_sticker["file_id"]

        file_response = requests.get(f"{TELEGRAM_API_URL}/getFile", params={"file_id": file_id})
        file_path = file_response.json()["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path}"
        file_extension = "tgs" if is_animated else "webm" if is_video else "png"
        temp_path = f"temp_{file_id}.{file_extension}"
        output_path = f"resized_{file_id}.webm"

        # Скачивание файла
        response = requests.get(file_url)
        with open(temp_path, "wb") as file:
            file.write(response.content)

        # Обработка видео в зависимости от типа пака
        if is_video:
            if new_pack_type == "sticker":
                process_video_for_sticker(temp_path, output_path)
            elif new_pack_type == "custom_emoji":
                process_video_for_emoji(temp_path, output_path)
            temp_path = output_path  # Обновляем путь к обработанному файлу

        # Если это обычное изображение, масштабируем его
        if not is_animated and not is_video:
            try:
                with Image.open(temp_path) as img:
                    img = img.convert("RGBA")
                    max_size = 512 if new_pack_type == "sticker" else 100
                    img.thumbnail((max_size, max_size), Image.LANCZOS)
                    new_img = Image.new("RGBA", (max_size, max_size), (0, 0, 0, 0))
                    x_offset = (max_size - img.width) // 2
                    y_offset = (max_size - img.height) // 2
                    new_img.paste(img, (x_offset, y_offset), img)
                    new_img.save(temp_path, "PNG")
            except UnidentifiedImageError:
                await message.reply("Ошибка: не удалось идентифицировать изображение.")
                return

        # Создание нового пака с первым стикером/эмодзи
        if new_pack_type == "sticker":
            data = {
                "user_id": user_id,
                "name": short_name,
                "title": pack_name,
                "emojis": first_sticker["emoji"],
                "sticker_type": "regular"
            }
            files = {
                "png_sticker" if not is_animated and not is_video else "tgs_sticker" if is_animated else "webm_sticker": open(temp_path, "rb")
            }
        elif new_pack_type == "custom_emoji":
            data = {
                "user_id": user_id,
                "name": short_name,
                "title": pack_name,
                "emojis": first_sticker["emoji"],
                "sticker_type": "custom_emoji"
            }
            files = {
                "png_sticker" if not is_animated and not is_video else "tgs_sticker" if is_animated else "webm_sticker": open(temp_path, "rb")
            }

        response = requests.post(f"{TELEGRAM_API_URL}/createNewStickerSet", data=data, files=files)

        if response.status_code != 200 or not response.json().get("ok"):
            await message.reply(f"Ошибка при создании нового пака: {response.json().get('description')}")
            return

        # Добавление оставшихся стикеров/эмодзи в новый пак
        for sticker in stickers[1:]:
            file_id = sticker["file_id"]
            is_animated = sticker.get("is_animated", False)
            is_video = sticker.get("is_video", False)
            file_response = requests.get(f"{TELEGRAM_API_URL}/getFile", params={"file_id": file_id})
            file_path = file_response.json()["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path}"
            file_extension = "tgs" if is_animated else "webm" if is_video else "png"
            temp_path = f"temp_{file_id}.{file_extension}"
            output_path = f"resized_{file_id}.webm"

            response = requests.get(file_url)
            with open(temp_path, "wb") as file:
                file.write(response.content)

            if is_video:
                if new_pack_type == "sticker":
                    process_video_for_sticker(temp_path, output_path)
                elif new_pack_type == "custom_emoji":
                    process_video_for_emoji(temp_path, output_path)
                temp_path = output_path

            if not is_animated and not is_video:
                try:
                    with Image.open(temp_path) as img:
                        img = img.convert("RGBA")
                        img.thumbnail((max_size, max_size), Image.LANCZOS)
                        new_img = Image.new("RGBA", (max_size, max_size), (0, 0, 0, 0))
                        x_offset = (max_size - img.width) // 2
                        y_offset = (max_size - img.height) // 2
                        new_img.paste(img, (x_offset, y_offset), img)
                        new_img.save(temp_path, "PNG")
                except UnidentifiedImageError:
                    await message.reply("Ошибка: не удалось идентифицировать одно из изображений. Пропускаем его.")
                    continue

            add_sticker_data = {
                "user_id": user_id,
                "name": short_name,
                "emojis": sticker["emoji"]
            }
            add_files_data = {
                "png_sticker" if not is_animated and not is_video else "tgs_sticker" if is_animated else "webm_sticker": open(temp_path, "rb")
            }

            add_response = requests.post(f"{TELEGRAM_API_URL}/addStickerToSet", data=add_sticker_data, files=add_files_data)

            if add_response.status_code != 200 or not add_response.json().get("ok"):
                await message.reply(f"Ошибка при добавлении стикера/эмодзи: {add_response.json().get('description')}")
                return

        pack_link = f"https://t.me/add{'stickers' if new_pack_type == 'sticker' else 'emoji'}/{short_name}"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔗 ОТКРЫТЬ ПАК", url=pack_link)]]
        )
        await message.reply("✅ Пак успешно создан!", reply_markup=keyboard)

        async with db_pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO sticker_packs (user_id, pack_name, short_name, set_type)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, pack_name, short_name, set_type
            )

    except Exception as e:
        await message.reply(f"Ошибка: {e}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        await processing_message.delete()
        await state.clear()

# ----------------------- ФУНКЦИИ СТИКЕРПАКА ----------------------- #

# Получение названия пака и запрос короткой ссылки
@dp.message(StateFilter(StickerPackForm.waiting_for_pack_name))
async def process_pack_name(message: types.Message, state: FSMContext):
    await state.update_data(pack_name=message.text)

    # Формируем сообщение с выделением текста жирным
    response_message = (
        "✅ *Название сохранено!*\n\n"
        "Теперь придумайте короткую ссылку на пак\n"
        "(только *английские буквы* и *цифры*, без пробела)\n\n"
        "*Пример*: `link123`"
    )

    # Создаем клавиатуру с кнопкой "Отмена"
    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
        ]
    )

    # Отправляем сообщение с инструкцией и клавиатурой
    await message.reply(response_message, reply_markup=cancel_keyboard, parse_mode="Markdown")

    # Устанавливаем состояние ожидания короткого имени
    await state.set_state(StickerPackForm.waiting_for_short_name)

# Проверка корректности short_name и запрос файлов
@dp.message(StateFilter(StickerPackForm.waiting_for_short_name))
async def process_short_name(message: types.Message, state: FSMContext):
    short_name = message.text.lower()

    # Проверка на корректность имени
    if not re.match(r'^[a-z][a-z0-9_]*$', short_name) or short_name == 'генерировать':
        response_message = (
            "❌ *К сожалению, это некорректная ссылка.*\n"
            "Ссылка может содержать только _английские буквы_, _цифры_ и _нижнее подчёркивание_, "
            "и не должна начинаться с цифры.\n\n"
            "Отправьте другую ссылку."
        )
        await message.reply(response_message, parse_mode="Markdown")
        return

    # Генерация имени, если указано "генерировать"
    user_data = await state.get_data()
    username = re.sub(r'[^a-zA-Z0-9_]', '', message.from_user.username or message.from_user.first_name).lower() or 'user'
    bot_info = await bot.get_me()
    bot_name = re.sub(r'[^a-zA-Z0-9_]', '', bot_info.username).lower()

    if short_name == 'генерировать':
        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
        short_name = f"{username}_pack_{unique_id}_by_{bot_name}".lower()
    else:
        short_name = f"{short_name}_by_{bot_name}"

    # Ограничиваем длину имени
    short_name = short_name[:64]

    # Обновляем данные в состоянии
    await state.update_data(short_name=short_name)

    # Сообщение об успешной проверке
    response_message = (
        "✅ *Ссылка сохранена!*\n\n"
        "📎 Теперь отправьте мне фото/видео/стикер/гифку/эмодзи/видео-кружок для добавления в пак"
    )
    # Создание клавиатуры с кнопкой "Отмена"
    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
        ]
    )

    # Отправляем сообщение с инструкцией и клавиатурой
    await message.reply(response_message, reply_markup=cancel_keyboard, parse_mode="Markdown")
    await state.set_state(StickerPackForm.waiting_for_sticker)

# Получение изображения, GIF или видео и создание стикерпакета
@dp.message(StateFilter(StickerPackForm.waiting_for_sticker), F.content_type.in_(['photo', 'document', 'video', 'animation']))
async def process_sticker(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    pack_name = user_data.get('pack_name') + " @STIKERS_official"
    short_name = user_data.get('short_name')
    set_type = user_data.get('set_type', 'regular')

    # Отправляем эмодзи песочных часов
    processing_message = await bot.send_message(chat_id=message.chat.id, text='⏳')

    # Инициализация переменных для временных файлов
    temp_path = None
    temp_video_path = None
    temp_webm_path = None

    try:
        sticker_file_path = None
        sticker_file_type = None

        if message.content_type == 'photo':
            # Обработка фотографии
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            temp_path = os.path.join("temp", f"{uuid.uuid4()}.png")
            await bot.download_file(file_info.file_path, temp_path)

            with Image.open(temp_path) as img:
                img = img.convert("RGBA")
                if img.width < 512 or img.height < 512:
                    img = img.resize((512, 512), Image.LANCZOS)
                img.thumbnail((512, 512))
                img.save(temp_path, format="PNG")

            sticker_file_path = temp_path
            sticker_file_type = 'png_sticker'

        elif message.content_type == 'document':
            # Обработка документов, включая webp
            file_info = await bot.get_file(message.document.file_id)
            mime_type = message.document.mime_type
            temp_path = os.path.join("temp", f"{uuid.uuid4()}")

            # Проверка MIME-типа для webp
            if mime_type == "image/webp":
                temp_path += ".webp"
            else:
                temp_path += ".png"

            await bot.download_file(file_info.file_path, temp_path)

            # Конвертируем webp в png, если необходимо, и изменяем размер
            with Image.open(temp_path) as img:
                img = img.convert("RGBA")
                if img.width < 512 or img.height < 512:
                    img = img.resize((512, 512), Image.LANCZOS)
                img.thumbnail((512, 512))
                if mime_type == "image/webp":
                    temp_path = temp_path.replace(".webp", ".png")
                img.save(temp_path, format="PNG")

            sticker_file_path = temp_path
            sticker_file_type = 'png_sticker'

        elif message.content_type in ['video', 'animation']:
            # Обработка видео или GIF
            file_id = message.video.file_id if message.content_type == 'video' else message.animation.file_id
            file_info = await bot.get_file(file_id)
            temp_video_path = os.path.join("temp", f"{uuid.uuid4()}.mp4")
            temp_webm_path = os.path.join("temp", f"{uuid.uuid4()}.webm")
            await bot.download_file(file_info.file_path, temp_video_path)

            # Конвертация видео в webm с использованием FFmpeg
            process_video(temp_video_path, temp_webm_path)
            sticker_file_path = temp_webm_path
            sticker_file_type = 'webm_sticker'

        if sticker_file_path:
            # Загружаем файл для создания стикера через API Telegram
            with open(sticker_file_path, 'rb') as sticker_file:
                files = {
                    sticker_file_type: sticker_file
                }
                data = {
                    'user_id': user_id,
                    'title': pack_name,
                    'name': short_name,
                    'sticker_type': set_type,
                    'emojis': '\U0001F680'
                }
                response = requests.post(f"{TELEGRAM_API_URL}/createNewStickerSet", data=data, files=files)
                if response.status_code == 200:
                    # Обновляем состояние с данными о паке
                    await state.update_data(pack_name=pack_name, short_name=short_name)
                    await state.set_state(StickerPackForm.adding_sticker)

                    stickerpack_link = f"https://t.me/addstickers/{short_name}"
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="Открыть стикерпак", url=stickerpack_link)],
                            [InlineKeyboardButton(text="Добавить еще", callback_data="add_sticker")]
                        ]
                    )
                    await message.reply("Стикерпак успешно создан!", reply_markup=keyboard)
                else:
                    await message.reply(f"Не удалось создать стикерпак: {response.json().get('description')}")

        # Внутри try перед удалением временных файлов
        async with db_pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO sticker_packs (user_id, pack_name, short_name, set_type)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, pack_name, short_name, set_type
            )

        # Удаляем временные файлы
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if temp_webm_path and os.path.exists(temp_webm_path):
            os.remove(temp_webm_path)
    except Exception as e:
        await message.reply(f"Не удалось создать стикерпак: {e}")
    finally:
        # Удаляем сообщение с песочными часами
        await processing_message.delete()

    # Сбрасываем состояние
    await state.set_state(StickerPackForm.adding_sticker)

# Функция для обработки видео в webm
def process_video(input_path: str, output_path: str):
    # Команда для обработки видео в формате .WEBM с кодеком VP9, изменением размера на 512x512 пикселей
    # и удалением черного фона
    command = [
        FFMPEG_PATH,
        "-i", input_path,
        "-vf", (
            "scale=512:512:force_original_aspect_ratio=decrease,"
            "pad=512:512:(ow-iw)/2:(oh-ih)/2,"
            "format=rgba,"
            "chromakey=black:0.1:0.0"
        ),
        "-c:v", "libvpx-vp9",
        "-b:v", "512k",  # Битрейт для хорошего качества видео
        "-r", "30",  # Частота кадров
        "-an",  # Удаление звука
        "-t", "3",  # Обрезка видео до 3 секунд
        "-loop", "0",  # Повторение анимации
        output_path
    ]
    subprocess.run(command, check=True)

# Обработка выбора стикерпака
@dp.callback_query(lambda c: c.data.startswith("pack_"))
async def handle_pack_selection(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        # Получаем ID выбранного пака
        if callback_query.data.startswith("pack_stats"):
            # Если data равно "pack_stats", не пытаться извлечь pack_id
            await show_pack_stats(callback_query, state)
            return
        
        pack_id = int(callback_query.data.split("_")[1])
    except (ValueError, IndexError):
        # Обрабатываем возможные ошибки при извлечении pack_id
        await callback_query.answer("Неверный формат данных для выбора пака.", show_alert=True)
        return

    # Получаем данные о всех стикерпаках из состояния
    data = await state.get_data()
    regular_packs = data.get('regular_packs', [])

    # Ищем выбранный пак по ID
    selected_pack = next((pack for pack in regular_packs if pack['id'] == pack_id), None)

    if not selected_pack:
        # Если пак не найден, уведомляем пользователя
        await callback_query.answer("Пак не найден.", show_alert=True)
        return

    # Получаем имя и короткое имя пака
    pack_name = selected_pack.get('pack_name')
    short_name = selected_pack.get('short_name')

    # Проверяем корректность данных
    if not pack_name or not short_name:
        await callback_query.answer("Ошибка: данные о паке некорректны.", show_alert=True)
        return

    # Сохраняем данные о выбранном стикерпаке в состояние
    await state.update_data(pack_id=pack_id, pack_name=pack_name, short_name=short_name)

    # Ссылка на стикерпак
    pack_link = f"https://t.me/addstickers/{short_name}"

    # Создание кнопок для меню управления стикерпаком
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 ОТКРЫТЬ ПАК", url=pack_link)],
        [InlineKeyboardButton(text="➕ Добавить к паку", callback_data="add_sticker")],
        [InlineKeyboardButton(text="✏️ Переименовать пак", callback_data="rename_pack")],
        [InlineKeyboardButton(text="🗑️ Удалить стикер из пака", callback_data="remove_sticker")],
        [InlineKeyboardButton(text="❗ Удалить весь пак", callback_data="delete_pack")],
        [InlineKeyboardButton(text="📊 Количество установок", callback_data="pack_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="show_regular_packs")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    ])

    # Формируем сообщение с информацией о паке
    response_message = (
        f"Управление набором\n\n"
        f"Выбран стикер-пак [{pack_name[:-16]}]({pack_link})\n\n"
        "В этом меню Вы можете управлять набором. Выберите действие по кнопке ниже."
    )

    # Обновляем сообщение с меню управления
    await callback_query.message.edit_text(response_message, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()  # Закрываем уведомление

# Хэндлер для кнопки "Добавить к паку"
@dp.callback_query(lambda c: c.data == "add_sticker")
async def add_sticker_handler(callback_query: types.CallbackQuery, state: FSMContext):
    # Получение данных о выбранном паке
    user_data = await state.get_data()
    pack_name = user_data.get('pack_name')
    short_name = user_data.get('short_name')

    # Создание клавиатуры с кнопкой "Отмена"
    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
        ]
    )

    # Сообщение с инструкцией и ссылкой на пак
    pack_link = f"https://t.me/addstickers/{short_name}"
    response_message = (
        f"Добавление стикеров/эмодзи в [{pack_name}]({pack_link})\n\n"
        "📎 Теперь отправьте мне фото/видео/стикер/гифку/эмодзи/видео-кружок для добавления в пак\n\n"
        "Ограничения tg: максимум 200 эмодзи, 50 гиф-стикеров, и 120 - обычных стикеров в одном паке"
    )

    await callback_query.message.edit_text(response_message, reply_markup=cancel_keyboard, parse_mode="Markdown")
    await state.set_state(StickerPackForm.adding_sticker)
    await callback_query.answer()

# Функция для удаления стикерпака
@dp.callback_query(lambda c: c.data == "delete_pack")
async def confirm_delete_sticker_pack(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные о выбранном стикерпаке
    data = await state.get_data()
    pack_name = data.get('pack_name')

    # Создание кнопок для подтверждения или отмены удаления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❗ Подтвердить удаление", callback_data="confirm_delete")],
        [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
    ])

    # Сообщение с предупреждением
    response_message = (
        f"Вы собираетесь удалить стикер-пак: {pack_name}\n\n"
        "Это действие необратимо. Нажмите 'Подтвердить удаление', чтобы удалить пак, или 'Отмена', чтобы вернуться в меню."
    )

    # Отправляем сообщение с кнопками подтверждения
    await callback_query.message.edit_text(response_message, reply_markup=keyboard)
    await state.set_state(StickerPackForm.confirming_deletion)  # Устанавливаем состояние подтверждения

# Обработка подтверждения удаления стикерпака
@dp.callback_query(lambda c: c.data == "confirm_delete", StateFilter(StickerPackForm.confirming_deletion))
async def delete_sticker_pack(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные о выбранном стикерпаке
    data = await state.get_data()
    short_name = data.get('short_name')
    pack_id = data.get('pack_id')

    # Удаление стикерпака из базы данных
    async with db_pool.acquire() as connection:
        await connection.execute(
            "DELETE FROM sticker_packs WHERE id = $1",
            pack_id
        )

    # Попытка удалить стикерпак через API Telegram
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{API_TOKEN}/deleteStickerSet",
            json={"name": short_name}
        )

        if response.status_code == 200 and response.json().get('ok'):
            await callback_query.message.reply("Стикерпак успешно удален из базы данных и API.")
        else:
            error_message = response.json().get("description", "Не удалось удалить стикерпак через API.")
            await callback_query.message.reply(f"Стикерпак удален из базы данных, но возникла ошибка при удалении через API: {error_message}")
    except Exception as e:
        await callback_query.message.reply(f"Стикерпак удален из базы данных, но возникла ошибка при удалении через API: {e}")

    # Очистка состояния
    await state.clear()

# Обработчик для добавления стикеров пачкой
@dp.message(StateFilter(StickerPackForm.adding_sticker), F.content_type.in_(['photo', 'document', 'video', 'animation']))
async def add_stickers_to_set(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    pack_name = user_data.get('pack_name')
    short_name = user_data.get('short_name')

    media_group_id = message.media_group_id
    processing_message = None  # Инициализация переменной

    if media_group_id and media_group_id not in media_group_processing_messages:
        processing_message = await bot.send_message(chat_id=message.chat.id, text='⏳')
        media_group_processing_messages[media_group_id] = processing_message

    # Функция для обработки всех файлов после завершения сбора
    async def process_media_group():
        messages = media_group_storage.pop(media_group_id, [])
        media_group_timers.pop(media_group_id, None)
        media_files = []

        # Обрабатываем каждый файл
        for msg in messages:
            file_info, temp_path, sticker_file_type = await process_message_file(msg)
            if file_info and temp_path:
                media_files.append((file_info, temp_path, sticker_file_type))

        total_added = 0  # Счётчик успешно добавленных стикеров

        try:
            # Загружаем файлы и добавляем в стикерпак
            for file_info, temp_path, sticker_file_type in media_files:
                with open(temp_path, 'rb') as sticker_file:
                    files = {sticker_file_type: sticker_file}
                    data = {
                        'user_id': user_id,
                        'title': pack_name,
                        'name': short_name,
                        'emojis': '\U0001F680'
                    }
                    response = requests.post(f"{TELEGRAM_API_URL}/addStickerToSet", data=data, files=files)
                    if response.status_code == 200 and response.json().get('ok'):
                        total_added += 1
                    else:
                        print(f"Не удалось добавить стикер: {response.json().get('description')}")

            # Формируем сообщение об успешном добавлении всех стикеров
            stickerpack_link = f"https://t.me/addstickers/{short_name}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 ОТКРЫТЬ ПАК", url=stickerpack_link)],
                    [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_sticker")]
                ]
            )
            await processing_message.edit_text(f"✅ Успешно добавлено {total_added} стикеров!", reply_markup=keyboard)

        except Exception as e:
            await processing_message.edit_text("❌ Не удалось добавить стикеры")
            print(f"Ошибка при добавлении стикеров: {e}")
        finally:
            # Удаляем временные файлы
            for _, temp_path, _ in media_files:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

            # Сохраняем данные стикерпакета в состояние перед завершением
            await state.update_data(pack_name=pack_name, short_name=short_name)
            # Сбрасываем состояние
            await state.set_state(StickerPackForm.adding_sticker)

    # Сохраняем сообщение в хранилище медиа-группы
    if media_group_id:
        if media_group_id not in media_group_storage:
            media_group_storage[media_group_id] = []
        media_group_storage[media_group_id].append(message)

        # Устанавливаем или обновляем таймер ожидания
        if media_group_id in media_group_timers:
            media_group_timers[media_group_id].cancel()  # Отменяем старый таймер
        loop = asyncio.get_event_loop()
        media_group_timers[media_group_id] = loop.call_later(WAIT_TIME, lambda: asyncio.create_task(process_media_group()))

    else:
        # Если сообщение не относится к медиа-группе, обрабатываем одиночное сообщение
        file_info, temp_path, sticker_file_type = await process_message_file(message)
        if file_info and temp_path:
            try:
                with open(temp_path, 'rb') as sticker_file:
                    files = {sticker_file_type: sticker_file}
                    data = {
                        'user_id': user_id,
                        'title': pack_name,
                        'name': short_name,
                        'emojis': '\U0001F680'
                    }
                    response = requests.post(f"{TELEGRAM_API_URL}/addStickerToSet", data=data, files=files)
                    if response.status_code == 200 and response.json().get('ok'):
                        stickerpack_link = f"https://t.me/addstickers/{short_name}"
                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text="🔗 ОТКРЫТЬ ПАК", url=stickerpack_link)],
                                [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_sticker")]
                            ]
                        )
                        # Код для отправки сообщения об успешном добавлении
                        await bot.send_message(chat_id=message.chat.id, text="✅ Стикер успешно добавлен!", reply_markup=keyboard)
                    else:
                        await bot.send_message(chat_id=message.chat.id, text="❌ Не удалось добавить стикер")
            except Exception as e:
                await bot.send_message(chat_id=message.chat.id, text="❌ Не удалось добавить стикер")
                print(f"Ошибка при добавлении стикера: {e}")
            finally:
                # Удаляем временный файл
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

                                # Сохраняем данные стикерпакета в состояние перед завершением
                await state.update_data(pack_name=pack_name, short_name=short_name)
                await state.set_state(StickerPackForm.adding_sticker)

# Функция для обработки файлов из сообщения
async def process_message_file(msg):
    try:
        temp_path = None
        sticker_file_type = None

        if msg.content_type == 'photo':
            # Обработка фотографии
            photo = msg.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            temp_path = os.path.join("temp", f"{uuid.uuid4()}.png")
            await bot.download_file(file_info.file_path, temp_path)

            with Image.open(temp_path) as img:
                img = img.convert("RGBA")
                # Изменяем размер только если изображение меньше 512x512
                if img.width < 512 or img.height < 512:
                    img = img.resize((512, 512), Image.LANCZOS)
                img.thumbnail((512, 512))
                img.save(temp_path, format="PNG")

            sticker_file_path = temp_path
            sticker_file_type = 'png_sticker'

        elif msg.content_type == 'document':
            # Обработка документа, включая изображения webp
            file_info = await bot.get_file(msg.document.file_id)
            mime_type = msg.document.mime_type
            temp_path = os.path.join("temp", f"{uuid.uuid4()}")

            # Определяем формат файла и скачиваем с правильным расширением
            if mime_type == "image/webp":
                temp_path += ".webp"
            else:
                temp_path += ".png"

            await bot.download_file(file_info.file_path, temp_path)

            # Конвертируем webp в png и изменяем размер
            with Image.open(temp_path) as img:
                img = img.convert("RGBA")
                if img.width < 512 or img.height < 512:
                    img = img.resize((512, 512), Image.LANCZOS)
                img.thumbnail((512, 512))
                temp_path = temp_path.replace(".webp", ".png")  # Обновляем путь с .png
                img.save(temp_path, format="PNG")

            sticker_file_path = temp_path
            sticker_file_type = 'png_sticker'

        elif msg.content_type in ['video', 'animation']:
            # Обработка видео или GIF
            file_id = msg.video.file_id if msg.content_type == 'video' else msg.animation.file_id
            file_info = await bot.get_file(file_id)
            temp_video_path = os.path.join("temp", f"{uuid.uuid4()}.mp4")
            temp_webm_path = os.path.join("temp", f"{uuid.uuid4()}.webm")
            await bot.download_file(file_info.file_path, temp_video_path)

            # Конвертация видео в webm с использованием FFmpeg
            process_video(temp_video_path, temp_webm_path)
            temp_path = temp_webm_path
            sticker_file_type = 'webm_sticker'

        return file_info, temp_path, sticker_file_type
    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")
        return None, None, None

# Обработка удаления стикера
@dp.message(StateFilter(StickerPackForm.removing_sticker), F.content_type.in_(['sticker']))
async def remove_sticker(message: types.Message, state: FSMContext):
    sticker_file_id = message.sticker.file_id

    try:
        # Отправляем запрос на удаление стикера из стикерпака
        response = requests.post(f"{TELEGRAM_API_URL}/deleteStickerFromSet", data={'sticker': sticker_file_id})
        
        if response.status_code == 200 and response.json().get('ok'):
            await message.reply("Стикер успешно удален из пака!")
        else:
            error_message = response.json().get('description', 'Неизвестная ошибка')
            await message.reply(f"Ошибка при удалении стикера: {error_message}")
            print(f"Ошибка при удалении стикера: {response.text}")

    except Exception as e:
        await message.reply(f"Не удалось удалить стикер: {e}")
        print(f"Исключение: {e}")

    # Сбрасываем состояние
    await state.clear()

# Обработка смены обложки
@dp.message(StateFilter(StickerPackForm.set_thumbnail), F.content_type.in_(['photo', 'document', 'video', 'animation']))
async def set_thumbnail(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    short_name = user_data.get('short_name')

    # Отправляем сообщение о процессе обновления
    processing_message = await bot.send_message(chat_id=message.chat.id, text='⏳')

    # Инициализация переменных для временных файлов
    temp_path = None
    temp_video_path = None
    temp_webm_path = None
    temp_gif_path = None

    try:
        temp_thumbnail_path = None
        thumbnail_format = None

        if message.content_type == 'photo':
            # Обработка отправленного фото
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            if file_info and file_info.file_path:  # Проверка, что file_info корректно получен
                temp_path = os.path.join("temp", f"{uuid.uuid4()}.webp")
                await bot.download_file(file_info.file_path, temp_path)
            else:
                raise ValueError("Не удалось получить информацию о файле")

        elif message.content_type == 'document' and message.document.mime_type.startswith('image'):
            # Обработка прикрепленного файла изображения
            file_info = await bot.get_file(message.document.file_id)
            if file_info and file_info.file_path:  # Проверка, что file_info корректно получен
                temp_path = os.path.join("temp", f"{uuid.uuid4()}.webp")
                await bot.download_file(file_info.file_path, temp_path)
            else:
                raise ValueError("Не удалось получить информацию о файле")

        if temp_path:
            # Открываем и обрабатываем изображение
            with Image.open(temp_path) as img:
                img = img.convert("RGBA")  # Конвертируем в RGBA для гарантии альфа-канала

                # Сохраняем исходное соотношение сторон и уменьшаем изображение до 100x100
                original_width, original_height = img.size
                scale = min(100 / original_width, 100 / original_height)
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                img = img.resize((new_width, new_height), Image.LANCZOS)

                # Создаем новый холст 100x100 с прозрачным фоном
                new_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
                x_offset = (100 - new_width) // 2
                y_offset = (100 - new_height) // 2
                new_img.paste(img, (x_offset, y_offset), img)  # Сохраняем прозрачность

                # Сохраняем изображение с улучшенным качеством и прозрачностью
                new_img.save(temp_path, format="WEBP")

            temp_thumbnail_path = temp_path
            thumbnail_format = 'static'

        if message.content_type == 'video':
            # Обработка видео
            file_id = message.video.file_id
            file_info = await bot.get_file(file_id)

            if file_info and file_info.file_path:  # Проверка, что file_info корректно получен
                temp_video_path = os.path.join("temp", f"{uuid.uuid4()}.mp4")
                temp_webm_path = os.path.join("temp", f"{uuid.uuid4()}.webm")
                await bot.download_file(file_info.file_path, temp_video_path)

                # Конвертация видео в webm с использованием FFmpeg
                try:
                    process_emoji_video(temp_video_path, temp_webm_path)
                    temp_thumbnail_path = temp_webm_path
                    thumbnail_format = 'video'
                except subprocess.CalledProcessError as e:
                    raise ValueError(f"Ошибка при обработке видео: {e}")

        elif message.content_type == 'animation':
            # Обработка GIF
            file_id = message.animation.file_id
            file_info = await bot.get_file(file_id)

            if file_info and file_info.file_path:  # Проверка, что file_info корректно получен
                temp_gif_path = os.path.join("temp", f"{uuid.uuid4()}.gif")
                temp_webm_path = os.path.join("temp", f"{uuid.uuid4()}.webm")
                await bot.download_file(file_info.file_path, temp_gif_path)

                # Конвертация GIF в webm с использованием FFmpeg
                try:
                    process_emoji_video(temp_gif_path, temp_webm_path)
                    temp_thumbnail_path = temp_webm_path
                    thumbnail_format = 'video'
                except subprocess.CalledProcessError as e:
                    raise ValueError(f"Ошибка при обработке GIF: {e}")

        if temp_thumbnail_path:
            with open(temp_thumbnail_path, 'rb') as thumbnail_file:
                files = {
                    'thumbnail': thumbnail_file
                }
                data = {
                    'name': short_name,
                    'user_id': user_id,
                    'format': thumbnail_format  # Используем "static" для изображений .WEBP
                }
                response = requests.post(f"{TELEGRAM_API_URL}/setStickerSetThumbnail", data=data, files=files)

                if response.status_code == 200 and response.json().get("ok"):
                    await message.reply("Обложка стикерпака успешно обновлена!")
                else:
                    await message.reply(f"Не удалось обновить обложку: {response.json().get('description')}")

        # Удаляем временные файлы
        if temp_thumbnail_path and os.path.exists(temp_thumbnail_path):
            os.remove(temp_thumbnail_path)
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if temp_webm_path and os.path.exists(temp_webm_path):
            os.remove(temp_webm_path)
        if temp_gif_path and os.path.exists(temp_gif_path):
            os.remove(temp_gif_path)

    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")
    finally:
        # Удаляем сообщение о процессе
        await processing_message.delete()
    # Сбрасываем состояние
    await state.clear()

@dp.message(StateFilter(StickerPackForm.renaming_pack))
async def rename_pack(message: types.Message, state: FSMContext):
    new_name = message.text.strip() + " @STIKERS_official"

    # Проверка на корректность имени
    if len(new_name) < 3 or len(new_name) > 64:
        await message.reply("Имя должно быть длиной от 3 до 64 символов. Попробуйте снова.")
        return

    # Извлекаем данные из состояния
    data = await state.get_data()
    pack_id = data.get('id')
    pack_name = data.get('pack_name')
    short_name = data.get('short_name')

    if not short_name or not pack_name:
        await message.reply("Ошибка: стикер-пак не выбран.")
        return

    # Отправляем запрос на переименование стикерпака
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{API_TOKEN}/setStickerSetTitle",
            data={
                "name": short_name,
                "title": new_name
            }
        )
        response_data = response.json()

        if response.status_code == 200 and response_data.get('ok'):
            # Обновляем название пака в базе данных
            try:
                async with db_pool.acquire() as connection:
                    await connection.execute(
                        """
                        UPDATE sticker_packs
                        SET pack_name = $1
                        WHERE short_name = $2
                        """,
                        new_name,
                        short_name
                    )
            except Exception as db_error:
                await message.reply("Ошибка при обновлении базы данных.")
                print(f"Ошибка при обновлении базы данных: {db_error}")
                return

            # Создаём клавиатуру с кнопками "ОТКРЫТЬ ПАК" и "В меню"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↗️ ОТКРЫТЬ ПАК", url=f"https://t.me/addstickers/{short_name}")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
            ])

            # Формируем сообщение об успешном переименовании
            response_message = (
                "✅ Пак успешно переименован!\n\n"
                f"{pack_name[:-18]} ➡️ {new_name[:-18]}"
            )

            # Отправляем сообщение с кнопками
            await message.reply(response_message, reply_markup=keyboard)
        else:
            error_message = response_data.get('description', 'Неизвестная ошибка')
            await message.reply(f"Ошибка при переименовании пака: {error_message}")
            print(f"Ошибка при переименовании пака: {response_data}")

    except Exception as e:
        await message.reply(f"Не удалось переименовать стикер-пак: {e}")
        print(f"Исключение: {e}")

    # Сбрасываем состояние
    await state.clear()

@dp.callback_query(lambda c: c.data == "pack_stats")
async def show_pack_stats(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные о выбранном стикерпаке
    data = await state.get_data()
    short_name = data.get('short_name')

    if not short_name:
        await callback_query.answer("Ошибка: стикер-пак не выбран.", show_alert=True)
        return

    # Формируем сообщение с инструкцией
    response_message = (
        "📊 Для просмотра статистики вам необходимо воспользоваться системным ботом @stickers — "
        "только он может показывать количество установок набора.\n\n"
        "🔍 Чтобы посмотреть статистику:\n"
        "1. Откройте системного бота @stickers.\n"
        "2. Введите команду: `/packstats`.\n"
        "3. Бот спросит выбрать стикер-пак, отправьте ему короткую ссылку на пак:\n"
        f"`{short_name}`\n\n"
        "Пример команды и результата можно увидеть на изображении ниже. "
        "Для получения более подробной статистики отправьте сообщение в формате "
        "MM/DD/YYYY, MM/YYYY, или YYYY."
    )

    # Создание клавиатуры с кнопкой для закрытия
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="menu")]
    ])

    # Отправляем сообщение с инструкцией и кнопкой "Закрыть"
    await callback_query.message.edit_text(
        response_message, 
        reply_markup=keyboard, 
        parse_mode="Markdown"
    )
    await callback_query.answer()  # Закрываем уведомление


# ----------------------- ФУНКЦИИ ЭМОДЗИПАКА ----------------------- #

# Получение названия пака и запрос short_link
# Обработчик для получения названия пака и запроса короткой ссылки
@dp.message(StateFilter(EmojiPackForm.waiting_for_pack_name))
async def process_emoji_pack_name(message: types.Message, state: FSMContext):
    # Сохраняем название пака в состояние
    await state.update_data(pack_name=message.text)

    # Создание клавиатуры с кнопкой "Отмена"
    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
        ]
    )

    # Формируем сообщение с инструкцией
    response_message = (
        "✅ *Название сохранено!*\n\n"
        "Теперь придумайте короткую ссылку на пак (только английские буквы и цифры, без пробела)\n\n"
        "Пример: `link123`"
    )

    # Отправляем сообщение с инструкцией и клавиатурой
    await message.reply(response_message, reply_markup=cancel_keyboard, parse_mode="Markdown")
    
    # Устанавливаем состояние ожидания короткого имени
    await state.set_state(EmojiPackForm.waiting_for_short_name)

# Получение short_link и запрос стикера
# Создание клавиатуры с кнопкой "Adaptive" и "Отмена"
def create_adaptive_keyboard(adaptive_enabled):
    adaptive_text = "Adaptive ✅" if adaptive_enabled else "Adaptive ❌"
    adaptive_callback_data = "toggle_adaptive"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=adaptive_text, callback_data=adaptive_callback_data)],
            [InlineKeyboardButton(text="✖ Отмена", callback_data="cancel")]
        ]
    )

# Обработчик для short_name
@dp.message(StateFilter(EmojiPackForm.waiting_for_short_name))
async def process_emoji_short_name(message: types.Message, state: FSMContext):
    short_name = message.text.lower()

    # Проверяем корректность имени
    if not re.match(r'^[a-z0-9_]+$', short_name) and short_name != 'генерировать':
        await message.reply("Имя должно содержать только латинские буквы, цифры и символы подчеркивания. Попробуйте снова:")
        return

    # Формируем short_name
    user_data = await state.get_data()
    username = re.sub(r'[^a-zA-Z0-9_]', '', message.from_user.username or message.from_user.first_name).lower()
    username = username if username else 'user'

    bot_info = await bot.get_me()
    bot_name = re.sub(r'[^a-zA-Z0-9_]', '', bot_info.username).lower()

    if short_name == 'генерировать':
        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
        short_name = f"{username}_pack_{unique_id}_by_{bot_name}".lower()
    else:
        short_name = f"{short_name}_by_{bot_name}"

    short_name = short_name[:64]  # Ограничиваем длину имени

    # Сохраняем short_name в состоянии
    await state.update_data(short_name=short_name, adaptive_enabled=False)

    # Создаем клавиатуру
    adaptive_keyboard = create_adaptive_keyboard(adaptive_enabled=False)

    # Отправляем сообщение с инструкцией
    await message.reply(
        "Ссылка сохранена ✅\n\n"
        "📎 Теперь отправьте мне фото/видео/стикер/гифку/эмодзи/видео-кружок для добавления в пак.\n\n"
        "Ограничения tg: максимум 200 эмодзи в наборе и 120 в обычном наборе стикеров.",
        reply_markup=adaptive_keyboard
    )

    # Устанавливаем состояние для ожидания стикера
    await state.set_state(EmojiPackForm.waiting_for_sticker)

# Обработчик для кнопки "Adaptive"
@dp.callback_query(lambda c: c.data == "toggle_adaptive")
async def handle_adaptive_button(callback_query: types.CallbackQuery, state: FSMContext):
    # Определяем текущий статус и переключаем
    user_data = await state.get_data()
    adaptive_enabled = not user_data.get("adaptive_enabled", False)
    await state.update_data(adaptive_enabled=adaptive_enabled)

    # Обновляем текст и клавиатуру
    text_message = (
        "Ссылка сохранена ✅\n\n"
        "📎 Теперь отправьте мне фото/видео/стикер/гифку/эмодзи/видео-кружок для добавления в пак.\n\n"
        "Ограничения tg: максимум 200 эмодзи в наборе и 120 в обычном наборе стикеров."
    )
    adaptive_keyboard = create_adaptive_keyboard(adaptive_enabled)

    # Редактируем предыдущее сообщение
    await callback_query.message.edit_text(text_message, reply_markup=adaptive_keyboard)
    await callback_query.answer()  # Убираем "часики" с кнопки

# Получение изображения, GIF или видео и создание стикерпакета
@dp.message(StateFilter(EmojiPackForm.waiting_for_sticker), F.content_type.in_(['photo', 'document', 'video', 'animation']))
async def process_emoji_sticker(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    pack_name = user_data.get('pack_name') + " @EMOJI_official"
    short_name = user_data.get('short_name')
    set_type = user_data.get('set_type', 'custom_emoji')
    adaptive_enabled = user_data.get('adaptive_enabled', False)  # Проверяем, включен ли адаптивный режим

    needs_repainting = adaptive_enabled

    # Отправляем эмодзи песочных часов
    processing_message = await bot.send_message(chat_id=message.chat.id, text='⏳')

    # Инициализация переменных для временных файлов
    temp_path = None
    temp_video_path = None
    temp_webm_path = None
    temp_gif_path = None

    try:
        sticker_file_path = None
        sticker_file_type = None

        if message.content_type == 'photo':
            # Обработка отправленного фото
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            if file_info and file_info.file_path:  # Проверка, что file_info корректно получен
                temp_path = os.path.join("temp", f"{uuid.uuid4()}.png")
                await bot.download_file(file_info.file_path, temp_path)
            else:
                raise ValueError("Не удалось получить информацию о файле")

        elif message.content_type == 'document' and message.document.mime_type.startswith('image'):
            # Обработка прикрепленного файла изображения
            file_info = await bot.get_file(message.document.file_id)
            if file_info and file_info.file_path:  # Проверка, что file_info корректно получен
                temp_path = os.path.join("temp", f"{uuid.uuid4()}.png")
                await bot.download_file(file_info.file_path, temp_path)
            else:
                raise ValueError("Не удалось получить информацию о файле")

        if temp_path:
            # Открываем и обрабатываем изображение
            with Image.open(temp_path) as img:
                img = img.convert("RGBA")  # Конвертируем в RGBA для гарантии альфа-канала

                # Сохраняем исходное соотношение сторон и уменьшаем изображение до 100x100
                original_width, original_height = img.size
                scale = min(100 / original_width, 100 / original_height)
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                img = img.resize((new_width, new_height), Image.LANCZOS)

                # Создаем новый холст 100x100 с прозрачным фоном
                new_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
                x_offset = (100 - new_width) // 2
                y_offset = (100 - new_height) // 2
                new_img.paste(img, (x_offset, y_offset), img)  # Сохраняем прозрачность

                # Сохраняем изображение с улучшенным качеством и прозрачностью
                new_img.save(temp_path, format="PNG")

            sticker_file_path = temp_path
            sticker_file_type = 'png_sticker'

        if message.content_type == 'video':
            # Обработка видео
            file_id = message.video.file_id
            file_info = await bot.get_file(file_id)

            if file_info and file_info.file_path:  # Проверка, что file_info корректно получен
                temp_video_path = os.path.join("temp", f"{uuid.uuid4()}.mp4")
                temp_webm_path = os.path.join("temp", f"{uuid.uuid4()}.webm")
                await bot.download_file(file_info.file_path, temp_video_path)

                # Конвертация видео в webm с использованием FFmpeg
                try:
                    process_emoji_video(temp_video_path, temp_webm_path)
                    sticker_file_path = temp_webm_path
                    sticker_file_type = 'webm_sticker'
                except subprocess.CalledProcessError as e:
                    raise ValueError(f"Ошибка при обработке видео: {e}")

        elif message.content_type == 'animation':
            # Обработка GIF
            file_id = message.animation.file_id
            file_info = await bot.get_file(file_id)

            if file_info and file_info.file_path:  # Проверка, что file_info корректно получен
                temp_gif_path = os.path.join("temp", f"{uuid.uuid4()}.gif")
                temp_webm_path = os.path.join("temp", f"{uuid.uuid4()}.webm")
                await bot.download_file(file_info.file_path, temp_gif_path)

                # Конвертация GIF в webm с использованием FFmpeg
                try:
                    process_emoji_video(temp_gif_path, temp_webm_path)
                    sticker_file_path = temp_webm_path
                    sticker_file_type = 'webm_sticker'
                except subprocess.CalledProcessError as e:
                    raise ValueError(f"Ошибка при обработке GIF: {e}")

        if sticker_file_path:
            # Загружаем файл для создания эмодзипака через API Telegram
            with open(sticker_file_path, 'rb') as sticker_file:
                url = f"{TELEGRAM_API_URL}/createNewStickerSet"

                # Определяем параметры запроса
                data = {
                    'user_id': user_id,
                    'name': short_name,
                    'title': pack_name,
                    'emojis': '\U0001F680',
                    'sticker_type': set_type,
                    'needs_repainting': needs_repainting
                }
                files = {
                    sticker_file_type: sticker_file
                }

                response = requests.post(url, data=data, files=files)
                if response.status_code == 200:
                    await state.update_data(pack_name=pack_name, short_name=short_name)
                    await state.set_state(EmojiPackForm.adding_sticker)

                    stickerpack_link = f"https://t.me/addemoji/{short_name}"
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔗 ОТКРЫТЬ ПАК", url=stickerpack_link)],
                            [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_esticker")]
                        ]
                    )
                    await message.reply("✅ Эмодзипак успешно создан!", reply_markup=keyboard)
                else:
                    await message.reply(f"Не удалось создать эмодзипак: {response.json().get('description')}")

        # Внутри try перед удалением временных файлов
        async with db_pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO sticker_packs (user_id, pack_name, short_name, set_type)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, pack_name, short_name, set_type
            )

        # Удаляем временные файлы
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if temp_webm_path and os.path.exists(temp_webm_path):
            os.remove(temp_webm_path)
        if temp_gif_path and os.path.exists(temp_gif_path):
            os.remove(temp_gif_path)

    except Exception as e:
        await message.reply(f"Не удалось создать эмодзипак: {e}")
    finally:
        # Удаляем сообщение с песочными часами
        await processing_message.delete()

    # Сбрасываем состояние
    await state.set_state(EmojiPackForm.adding_sticker)

# Функция для обработки видео и GIF в webm с прозрачностью
def process_emoji_video(input_path: str, output_path: str):
    # Команда для обработки видео в формате .WEBM с кодеком VP9, изменением размера на 100x100 пикселей
    command = [
        FFMPEG_PATH,
        "-i", input_path,
        "-vf", "scale=100:100:force_original_aspect_ratio=decrease,pad=100:100:(ow-iw)/2:(oh-ih)/2:color=0x00000000,colorkey=0x000000:0.3:0.1",  # Убираем черный цвет (0x000000) с порогами
        "-c:v", "libvpx-vp9",
        "-b:v", "256k",  # Битрейт для сжатия видео
        "-r", "30",  # Частота кадров
        "-an",  # Удаление звука
        "-pix_fmt", "yuva420p",  # Формат пикселей для сохранения прозрачности
        "-t", "3",  # Обрезка видео до 3 секунд
        output_path
    ]
    subprocess.run(command, check=True)

# Обработка выбора эмодзипака
@dp.callback_query(lambda c: c.data.startswith("emoji_pack_"))
async def handle_emoji_pack_selection(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        # Получаем ID выбранного эмодзипака
        if callback_query.data.startswith("emoji_pack_stats"):
            # Если data равно "emoji_pack_stats", не пытаться извлечь pack_id
            await show_emoji_packs(callback_query, state)
            return
        
        pack_id = int(callback_query.data.split("_")[2])
    except (ValueError, IndexError):
        # Обрабатываем возможные ошибки при извлечении pack_id
        await callback_query.answer("Неверный формат данных для выбора пака.", show_alert=True)
        return

    # Получаем данные о всех эмодзипаках из состояния
    data = await state.get_data()
    emoji_packs = data.get('emoji_packs', [])

    # Ищем выбранный эмодзипак по ID
    selected_pack = next((pack for pack in emoji_packs if pack['id'] == pack_id), None)

    if not selected_pack:
        # Если пак не найден, уведомляем пользователя
        await callback_query.answer("Эмодзипак не найден.", show_alert=True)
        return

    # Получаем имя и короткое имя пака
    pack_name = selected_pack.get('pack_name')
    short_name = selected_pack.get('short_name')

    # Проверяем корректность данных
    if not pack_name or not short_name:
        await callback_query.answer("Ошибка: данные о эмодзипаке некорректны.", show_alert=True)
        return

    # Сохраняем данные о выбранном эмодзипаке в состояние
    await state.update_data(pack_id=pack_id, pack_name=pack_name, short_name=short_name)

    # Ссылка на эмодзипак
    pack_link = f"https://t.me/addemoji/{short_name}"

    # Создание кнопок для меню управления эмодзипаком
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 ОТКРЫТЬ ПАК", url=pack_link)],
        [InlineKeyboardButton(text="➕ Добавить к паку", callback_data="add_esticker")],
        [InlineKeyboardButton(text="✏️ Переименовать пак", callback_data="rename_emoji_pack")],
        [InlineKeyboardButton(text="🗑️ Удалить эмодзи из пака", callback_data="delete_emoji")],
        [InlineKeyboardButton(text="❗ Удалить весь пак", callback_data="delete_pack")],
        [InlineKeyboardButton(text="📊 Количество установок", callback_data="pack_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="show_emoji_packs")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    ])

    # Формируем сообщение с информацией о эмодзипаке
    response_message = (
        f"Управление эмодзипаком\n\n"
        f"Выбран эмодзи-пак [{pack_name[:-16]}]({pack_link})\n\n"
        "В этом меню Вы можете управлять набором. Выберите действие по кнопке ниже."
    )

    # Обновляем сообщение с меню управления
    await callback_query.message.edit_text(response_message, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()  # Закрываем уведомление

# Функция для удаления стикерпака
async def delete_emoji_pack(callback_query: types.CallbackQuery, state: FSMContext):
    # Получение данных о выбранном стикерпаке
    data = await state.get_data()
    short_name = data.get('short_name')
    pack_id = data.get('pack_id')

    # Удаление стикерпака из базы данных
    async with db_pool.acquire() as connection:
        await connection.execute(
            "DELETE FROM sticker_packs WHERE id = $1",
            pack_id
        )

    # Попытка удалить стикерпак через API Telegram
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{API_TOKEN}/deleteStickerSet",
            json={"name": short_name}
        )

        if response.status_code == 200 and response.json().get('ok'):
            await callback_query.message.reply("Стикерпак успешно удален из базы данных и API.")
        else:
            error_message = response.json().get("description", "Не удалось удалить стикерпак через API.")
            await callback_query.message.reply(f"Стикерпак удален из базы данных, но возникла ошибка при удалении через API: {error_message}")
    except Exception as e:
        await callback_query.message.reply(f"Стикерпак удален из базы данных, но возникла ошибка при удалении через API: {e}")

    # Очистка состояния
    await state.clear()

# Хэндлер для кнопки "Добавить к паку"
@dp.callback_query(lambda c: c.data == "add_esticker")
async def add_sticker_handler(callback_query: types.CallbackQuery, state: FSMContext):
    # Получение данных о выбранном паке
    user_data = await state.get_data()
    pack_name = user_data.get('pack_name')
    short_name = user_data.get('short_name')

    # Создание клавиатуры с кнопкой "Отмена"
    cancel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
        ]
    )

    # Сообщение с инструкцией и ссылкой на пак
    pack_link = f"https://t.me/addstickers/{short_name}"
    response_message = (
        f"Добавление стикеров/эмодзи в [{pack_name}]({pack_link})\n\n"
        "📎 Теперь отправьте мне фото/видео/стикер/гифку/эмодзи/видео-кружок для добавления в пак\n\n"
        "Ограничения tg: максимум 200 эмодзи, 50 гиф-стикеров, и 120 - обычных стикеров в одном паке"
    )

    await callback_query.message.edit_text(response_message, reply_markup=cancel_keyboard, parse_mode="Markdown")
    await state.set_state(EmojiPackForm.adding_sticker)
    await callback_query.answer()

# Обработка добавления стикера
# Хранилище сообщений с медиа-файлами
media_queue = []

@dp.message(StateFilter(EmojiPackForm.adding_sticker), F.content_type.in_(['photo', 'document', 'video', 'animation']))
async def add_emoji_to_set(message: types.Message, state: FSMContext):
    global media_queue
    media_queue.append(message)

    # Если это первое сообщение, показываем песочные часы
    if len(media_queue) == 1:
        await bot.send_message(chat_id=message.chat.id, text='⏳ Обработка ваших файлов... Пожалуйста, подождите.')

    # Начинаем обработку медиа-файлов в фоновом режиме
    asyncio.create_task(process_media_queue(state))

# Обработчик сообщения для переименования эмодзипака
@dp.message(StateFilter(EmojiPackForm.renaming_pack))
async def rename_pack(message: types.Message, state: FSMContext):
    new_name = message.text.strip() + " @EMOJI_official"

    # Проверка на корректность имени
    if len(new_name) < 3 or len(new_name) > 64:
        await message.reply("Имя должно быть длиной от 3 до 64 символов. Попробуйте снова.")
        return

    # Извлекаем данные из состояния
    data = await state.get_data()
    pack_id = data.get('id')
    pack_name = data.get('pack_name')
    short_name = data.get('short_name')

    if not short_name or not pack_name:
        await message.reply("Ошибка: эмодзипак не выбран.")
        return

    # Отправляем запрос на переименование эмодзипака
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{API_TOKEN}/setStickerSetTitle",
            data={
                "name": short_name,
                "title": new_name
            }
        )
        response_data = response.json()

        if response.status_code == 200 and response_data.get('ok'):
            # Обновляем название пака в базе данных
            try:
                async with db_pool.acquire() as connection:
                    await connection.execute(
                        """
                        UPDATE sticker_packs
                        SET pack_name = $1
                        WHERE short_name = $2
                        """,
                        new_name,
                        short_name
                    )
            except Exception as db_error:
                await message.reply("Ошибка при обновлении базы данных.")
                print(f"Ошибка при обновлении базы данных: {db_error}")
                return

            # Создаем клавиатуру с кнопками "ОТКРЫТЬ ПАК" и "В меню"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↗️ ОТКРЫТЬ ПАК", url=f"https://t.me/addemoji/{short_name}")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
            ])

            # Формируем сообщение об успешном переименовании
            response_message = (
                "✅ Пак успешно переименован!\n\n"
                f"{pack_name[:-16]} ➡️ {new_name[:-16]}"
            )

            # Отправляем сообщение с кнопками
            await message.reply(response_message, reply_markup=keyboard)
        else:
            error_message = response_data.get('description', 'Неизвестная ошибка')
            await message.reply(f"Ошибка при переименовании пака: {error_message}")
            print(f"Ошибка при переименовании пака: {response_data}")

    except Exception as e:
        await message.reply(f"Не удалось переименовать эмодзипак: {e}")
        print(f"Исключение: {e}")

    # Сбрасываем состояние
    await state.clear()

@dp.callback_query(lambda c: c.data == "delete_emoji")
async def start_delete_emoji(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем данные о выбранном эмодзипаке
    data = await state.get_data()
    short_name = data.get("short_name")

    if not short_name:
        await callback_query.answer("Ошибка: эмодзи-пак не выбран.", show_alert=True)
        return

    # Запрашиваем информацию о наборе эмодзи
    response = requests.get(f"{TELEGRAM_API_URL}/getStickerSet", params={"name": short_name})
    response_data = response.json()

    if not response_data.get("ok"):
        await callback_query.answer("Ошибка при получении информации о наборе.", show_alert=True)
        return

    stickers = response_data.get("result", {}).get("stickers", [])
    
    # Сохраняем список стикеров в состояние
    await state.update_data(stickers=stickers)

    # Создаём клавиатуру с кнопкой "Отмена"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖ Отмена", callback_data="menu")]
    ])

    # Отправляем инструкцию
    await callback_query.message.edit_text(
        "Удаление эмодзи из набора\n\nПришлите эмодзи из этого набора, который хотите удалить.",
        reply_markup=keyboard
    )
    await state.set_state(EmojiPackForm.deleting_emoji)
    await callback_query.answer()

@dp.message(StateFilter(EmojiPackForm.deleting_emoji))
async def delete_emoji(message: types.Message, state: FSMContext):
    emoji = message.text.strip()

    # Получаем стикеры из состояния
    data = await state.get_data()
    stickers = data.get("stickers", [])

    # Ищем file_id для удаляемого эмодзи
    matching_sticker = next((sticker for sticker in stickers if sticker.get("emoji") == emoji), None)

    if not matching_sticker:
        await message.reply("Ошибка: эмодзи не найден в наборе.")
        return

    file_id = matching_sticker.get("file_id")

    if not file_id:
        await message.reply("Ошибка при получении file_id эмодзи.")
        return

    # Удаляем эмодзи с помощью /deleteStickerFromSet
    delete_response = requests.post(
        f"{TELEGRAM_API_URL}/deleteStickerFromSet",
        data={"sticker": file_id}
    )
    delete_response_data = delete_response.json()

    if delete_response_data.get("ok"):
        # Успешное удаление
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
        ])
        await message.reply("🗑️ Эмодзи успешно удалён из набора.", reply_markup=keyboard)
    else:
        error_message = delete_response_data.get("description", "Неизвестная ошибка")
        await message.reply(f"Ошибка при удалении эмодзи: {error_message}")

    # Сбрасываем состояние
    await state.clear()

async def process_media_queue(state: FSMContext):
    global media_queue

    while media_queue:
        message = media_queue.pop(0)  # Извлекаем первое сообщение из очереди

        user_data = await state.get_data()
        user_id = message.from_user.id
        pack_name = user_data.get('pack_name')
        short_name = user_data.get('short_name')

        # Инициализация переменных для временных файлов
        temp_path = None
        temp_video_path = None
        temp_webm_path = None
        temp_gif_path = None

        try:
            sticker_file_path = None
            sticker_file_type = None

            if message.content_type == 'photo':
                # Обработка фотографии
                photo = message.photo[-1]
                file_info = await bot.get_file(photo.file_id)
                temp_path = os.path.join("temp", f"{uuid.uuid4()}.png")
                await bot.download_file(file_info.file_path, temp_path)

                with Image.open(temp_path) as img:
                    img = img.convert("RGBA")
                    img.thumbnail((100, 100))
                    new_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
                    x_offset = (100 - img.width) // 2
                    y_offset = (100 - img.height) // 2
                    new_img.paste(img, (x_offset, y_offset), img)
                    new_img.save(temp_path, format="PNG")

                sticker_file_path = temp_path
                sticker_file_type = 'png_sticker'

            elif message.content_type == 'document' and message.document.mime_type.startswith('image'):
                # Обработка изображения из документа
                file_info = await bot.get_file(message.document.file_id)
                temp_path = os.path.join("temp", f"{uuid.uuid4()}.png")
                await bot.download_file(file_info.file_path, temp_path)
                # Обработка аналогична фото
                with Image.open(temp_path) as img:
                    img = img.convert("RGBA")
                    img.thumbnail((100, 100))
                    new_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
                    x_offset = (100 - img.width) // 2
                    y_offset = (100 - img.height) // 2
                    new_img.paste(img, (x_offset, y_offset), img)
                    new_img.save(temp_path, format="PNG")

                sticker_file_path = temp_path
                sticker_file_type = 'png_sticker'

            elif message.content_type == 'video':
                # Обработка видео
                file_info = await bot.get_file(message.video.file_id)
                temp_video_path = os.path.join("temp", f"{uuid.uuid4()}.mp4")
                temp_webm_path = os.path.join("temp", f"{uuid.uuid4()}.webm")
                await bot.download_file(file_info.file_path, temp_video_path)
                process_emoji_video(temp_video_path, temp_webm_path)
                sticker_file_path = temp_webm_path
                sticker_file_type = 'webm_sticker'

            elif message.content_type == 'animation':
                # Обработка анимации (GIF)
                file_info = await bot.get_file(message.animation.file_id)
                temp_gif_path = os.path.join("temp", f"{uuid.uuid4()}.gif")
                temp_webm_path = os.path.join("temp", f"{uuid.uuid4()}.webm")
                await bot.download_file(file_info.file_path, temp_gif_path)
                process_emoji_video(temp_gif_path, temp_webm_path)
                sticker_file_path = temp_webm_path
                sticker_file_type = 'webm_sticker'

            if sticker_file_path:
                # Загружаем файл для создания стикера через API Telegram
                with open(sticker_file_path, 'rb') as sticker_file:
                    files = {
                        sticker_file_type: sticker_file
                    }
                    data = {
                        'user_id': user_id,
                        'title': pack_name,
                        'name': short_name,
                        'emojis': '\U0001F680'
                    }
                    response = requests.post(f"{TELEGRAM_API_URL}/addStickerToSet", data=data, files=files)
                    if response.status_code == 200:
                        stickerpack_link = f"https://t.me/addemoji/{short_name}"
                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text="🔗 ОТКРЫТЬ ПАК", url=stickerpack_link)],
                                [InlineKeyboardButton(text="➕ Добавить еще", callback_data="add_sticker")]
                            ]
                        )
                        await message.reply("Стикер успешно добавлен!", reply_markup=keyboard)
                    else:
                        await message.reply(f"Не удалось добавить стикер: {response.json().get('description')}")

            # Удаление временных файлов
            for temp_file in [temp_path, temp_video_path, temp_webm_path, temp_gif_path]:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)

        except Exception as e:
            await message.reply(f"Не удалось добавить стикер: {e}")

        # Возвращаем состояние
        await state.update_data(pack_name=pack_name, short_name=short_name)
        await state.set_state(EmojiPackForm.adding_sticker)

# ----------------------- ЗАПУСК ----------------------- #

# Запуск бота
async def main():
    global db_pool
    db_pool = await create_db_pool()

    if not os.path.exists("temp"):
        os.makedirs("temp")
    
    # Регистрация диспетчера с ботом
    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")

# ----------------------- INFO ----------------------- #

# MADE BY ANOKHIN MAKSIM FOR @EmojiOfficial_bot
# ALL RIGHTS RESERVED BY MIT. LICENSE