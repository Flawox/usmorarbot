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

@dp.message(F.text.startswith("/broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID: return 
    
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        await message.answer("⚠️ Введите текст. Пример: `/broadcast Всем привет!`", parse_mode="Markdown")
        return
        
    count = 0
    for user_id in list(known_users):
        try:
            await bot.send_message(user_id, f"📢 <b>Оповещение:</b>\n\n{text_to_send}", parse_mode="HTML")
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
