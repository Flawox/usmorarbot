import asyncio
import os
import re
import threading
from flask import Flask
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.web_app_info import WebAppInfo
from aiogram.filters import CommandStart

load_dotenv()

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7195495745  # Твой Telegram ID
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Множество для хранения ID пользователей в оперативной памяти
known_users = set()


# ================= ЛОГИКА БАЗЫ ДАННЫХ TELEGRAM =================
async def load_db_from_channel():
    """Загружает ID пользователей из закрепленного сообщения в канале при старте бота."""
    if not DB_CHANNEL_ID:
        print("❌ ОШИБКА: DB_CHANNEL_ID не указан в .env")
        return
        
    try:
        # Очищаем ID от случайных кавычек из .env
        clean_channel_id = str(DB_CHANNEL_ID).replace('"', '').replace("'", "").strip()
        chat = await bot.get_chat(clean_channel_id)
        
        # Получаем закрепленное сообщение
        pinned = chat.pinned_message
        
        if pinned and pinned.text and "USERS_DB" in pinned.text:
            # Ищем ВСЕ последовательности цифр в тексте (надежный способ)
            ids = re.findall(r'\d+', pinned.text)
            
            for uid in ids:
                # Фильтруем случайные цифры (ID обычно длинные)
                if len(uid) > 5:
                    known_users.add(int(uid))
                    
            print(f"✅ База данных успешно загружена! В ней {len(known_users)} пользователей.")
        else:
            print("❌ В канале нет текстового закрепленного сообщения 'USERS_DB'. Напишите в канал /init_db")
            
    except Exception as e:
        print(f"❌ Критическая ошибка при загрузке БД из канала: {e}")


async def sync_user_to_db(user_id: int):
    """Добавляет нового пользователя в канал, если его там еще нет."""
    if user_id in known_users: 
        return
        
    known_users.add(user_id)
    if not DB_CHANNEL_ID: 
        return
    
    try:
        clean_channel_id = str(DB_CHANNEL_ID).replace('"', '').replace("'", "").strip()
        chat = await bot.get_chat(clean_channel_id)
        pinned = chat.pinned_message
        
        if pinned and pinned.text and "USERS_DB" in pinned.text:
            if str(user_id) not in pinned.text:
                new_text = pinned.text + f"\n{user_id}"
                
                # Лимит Telegram на длину сообщения - 4096 символов
                if len(new_text) < 4000:
                    await bot.edit_message_text(
                        chat_id=clean_channel_id, 
                        message_id=pinned.message_id, 
                        text=new_text
                    )
    except Exception as e:
        print(f"❌ Ошибка при добавлении юзера {user_id} в канал: {e}")


# ================= ХЭНДЛЕРЫ =================

# 1. Приветствие и кнопка Mini App
@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Сохраняем пользователя в БД для рассылок
    await sync_user_to_db(message.from_user.id) 
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Открыть приложение", web_app=WebAppInfo(url="https://usmorarapp.vercel.app/"))]
    ])
    
    welcome_text = (
        "🏛 Добро пожаловать!\n\n"
        "📱 Теперь все функции доступны в нашем приложении.\n"
        "Нажмите на кнопку ниже, чтобы открыть его."
    )
    
    await message.answer(welcome_text, reply_markup=markup)


# 2. Создание базы данных (Нужно написать /init_db прямо в канал)
@dp.channel_post(F.text == "/init_db")
async def init_db_in_channel(message: Message):
    channel_id = message.chat.id
    msg = await message.answer(f"USERS_DB:\n{ADMIN_ID}")
    await bot.pin_chat_message(chat_id=channel_id, message_id=msg.message_id) 
    await message.answer(f"✅ База данных успешно создана и закреплена!\nЗапишите этот ID в переменные окружения Render как `DB_CHANNEL_ID`.", parse_mode="Markdown")


# 3. Ручная рассылка (текст, фото, кружочки и т.д.)
@dp.message(F.text.startswith("/broadcast") | F.caption.startswith("/broadcast"))
async def cmd_broadcast(message: Message):
    # Защита: только ты можешь делать рассылку
    if message.from_user.id != ADMIN_ID: 
        return 
    
    count = 0
    known_users_list = list(known_users) 
    
    # Способ А: Если ты сделал Reply (Ответить) на готовый пост
    if message.reply_to_message:
        for user_id in known_users_list:
            try:
                await message.reply_to_message.copy_to(chat_id=user_id)
                count += 1
            except Exception: pass
            
    # Способ Б: Если ты написал команду сразу с текстом или прикрепил к фото
    else:
        content = (message.text or message.caption or "").replace("/broadcast", "").strip()
        has_media = bool(message.photo or message.video or message.document or message.animation or message.voice or message.audio)
        
        if not content and not has_media:
            await message.answer(
                "⚠️ *Внимание!*\n"
                "Введите текст или прикрепите медиа.\n"
                "Пример: `/broadcast Всем привет!`\n"
                "Или ответьте на готовое сообщение командой `/broadcast`", 
                parse_mode="Markdown"
            )
            return

        for user_id in known_users_list:
            try:
                if has_media:
                    caption = f"📢 <b>Оповещение:</b>\n\n{content}" if content else "📢 <b>Оповещение</b>"
                    await message.copy_to(chat_id=user_id, caption=caption, parse_mode="HTML")
                else:
                    await bot.send_message(chat_id=user_id, text=f"📢 <b>Оповещение:</b>\n\n{content}", parse_mode="HTML")
                count += 1
            except Exception: pass 
            
    await message.answer(f"✅ Рассылка завершена! Отправлено {count} пользователям.")


# ================= МИКРО-СЕРВЕР ДЛЯ RENDER (Keep-alive) =================
app = Flask(__name__)

@app.route('/')
def home(): 
    return "USM Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def start_web_server():
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()


# ================= ЗАПУСК БОТА =================
async def main():
    # Загружаем базу перед стартом бота
    await load_db_from_channel() 
    
    print("🚀 Бот запущен и готов к работе!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    start_web_server()
    asyncio.run(main())
