import asyncio
import os
import threading
from flask import Flask
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command

load_dotenv()

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7195495745  # Твой Telegram ID
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

known_users = set()

# ================= ЛОГИКА БАЗЫ ДАННЫХ TELEGRAM =================
async def load_db_from_channel():
    if not DB_CHANNEL_ID: return
    try:
        chat = await bot.get_chat(DB_CHANNEL_ID)
        pinned = chat.pinned_message
        if pinned and "USERS_DB" in pinned.text:
            ids = pinned.text.split("\n")[1:]
            for uid in ids:
                if uid.strip().isdigit():
                    known_users.add(int(uid.strip()))
            print(f"✅ База данных загружена: {len(known_users)} пользователей.")
    except Exception as e:
        print(f"❌ Ошибка загрузки БД: {e}")

async def sync_user_to_db(user_id: int):
    if user_id in known_users: return
    known_users.add(user_id)
    if not DB_CHANNEL_ID: return
    
    try:
        chat = await bot.get_chat(DB_CHANNEL_ID)
        pinned = chat.pinned_message
        if pinned and "USERS_DB" in pinned.text:
            if str(user_id) not in pinned.text:
                new_text = pinned.text + f"\n{user_id}"
                if len(new_text) < 4000:
                    await bot.edit_message_text(chat_id=DB_CHANNEL_ID, message_id=pinned.message_id, text=new_text)
    except Exception as e:
        print(f"❌ Ошибка сохранения юзера: {e}")

# ================= КЛАВИАТУРЫ =================
def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url="https://usmorarapp.vercel.app/"))]
    ])

# ================= ХЭНДЛЕРЫ =================
@dp.message(F.chat.type == "private", Command("pdfid"))
@dp.message(F.chat.type == "private", F.document)
async def pdf_file_id(message: Message):
    if not message.from_user or message.from_user.id != ADMIN_ID:
        return

    document = message.document
    if document is None and message.reply_to_message:
        document = message.reply_to_message.document

    if document is None:
        await message.answer("Пришли PDF-файл или ответь на него командой /pdfid.")
        return

    await message.answer(document.file_id, parse_mode=None)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await sync_user_to_db(message.from_user.id) 
    
    welcome_text = (
        "🏛 Добро пожаловать!\n"
        "📱 Узнать актуальное расписание, погоду, оценки за тесты, общие оценки и посещение.\n\n"
        "Нажми на кнопку ниже, чтобы открыть приложение:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_kb())

@dp.channel_post(F.text == "/init_db")
async def init_db_in_channel(message: Message):
    channel_id = message.chat.id
    msg = await message.answer(f"USERS_DB:\n{ADMIN_ID}")
    await bot.pin_chat_message(chat_id=channel_id, message_id=msg.message_id) 
    await message.answer(f"✅ База данных успешно создана и закреплена!\nЗапиши этот ID в переменные окружения Render как `DB_CHANNEL_ID`.", parse_mode="Markdown")

# Обновленный хэндлер для рассылки с фото
