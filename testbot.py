import asyncio
import os
import threading
from flask import Flask
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart

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
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await sync_user_to_db(message.from_user.id) 
    
    welcome_text = (
        "🏛 Добро пожаловать в расписание USM!\n\n"
        "📱 Здесь можно узнать актуальное расписание, погоду, оценки за тесты, общие оценки и посещение.\n\n"
        "Нажмите на кнопку ниже, чтобы открыть приложение:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_kb())

@dp.channel_post(F.text == "/init_db")
async def init_db_in_channel(message: Message):
    channel_id = message.chat.id
    msg = await message.answer(f"USERS_DB:\n{ADMIN_ID}")
    await bot.pin_chat_message(chat_id=channel_id, message_id=msg.message_id) 
    await message.answer(f"✅ База данных успешно создана и закреплена!.", parse_mode="Markdown")

@dp.message(F.text.startswith("/broadcast") | F.caption.startswith("/broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID: return 
    
    count = 0
    known_users_list = list(known_users) # Предполагается, что known_users у тебя определен где-то выше
    
    # 1. Если это ответ на сообщение (Reply)
    if message.reply_to_message:
        for user_id in known_users_list:
            try:
                await message.reply_to_message.copy_to(chat_id=user_id)
                count += 1
            except Exception: pass
            
    # 2. Если это команда с текстом или медиа
    else:
        # Достаем текст или подпись к медиа
        content = (message.text or message.caption or "").replace("/broadcast", "").strip()
        has_media = bool(message.photo or message.video or message.document or message.animation)
        
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
                    # Рассылка картинки/видео с новым текстом (без команды)
                    # Если content пустой, отправляем медиа без подписи
                    caption = f"📢 <b>Оповещение:</b>\n\n{content}" if content else "📢 <b>Оповещение</b>"
                    await message.copy_to(chat_id=user_id, caption=caption, parse_mode="HTML")
                else:
                    # Обычная текстовая рассылка
                    await bot.send_message(chat_id=user_id, text=f"📢 <b>Оповещение:</b>\n\n{content}", parse_mode="HTML")
                count += 1
            except Exception: pass 
            
    await message.answer(f"✅ Рассылка завершена! Отправлено {count} пользователям.")

# ================= МИКРО-СЕРВЕР ДЛЯ RENDER =================
app = Flask(__name__)

@app.route('/')
def home(): 
    return "Bot is running on Render!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def start_web_server():
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

# ================= ЗАПУСК =================
async def main():
    await load_db_from_channel() 
    
    # Отправка сообщения в канал базы данных при запуске
    if DB_CHANNEL_ID:
        try:
            await bot.send_message(
                chat_id=DB_CHANNEL_ID,
                text=f"🟢 База данных активна. Количество пользователей: {len(known_users)}"
            )
        except Exception as e:
            print(f"❌ Ошибка отправки статуса в канал: {e}")
            
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    start_web_server()
    asyncio.run(main())
