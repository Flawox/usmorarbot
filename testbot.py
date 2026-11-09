import asyncio
import os
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

known_users = set()


# ================= ЛОГИКА БАЗЫ ДАННЫХ TELEGRAM =================
async def load_db_from_channel():
    if not DB_CHANNEL_ID: 
        print("❌ DB_CHANNEL_ID не найден в .env")
        return
        
    try:
        # Для приватных групп ID обязан быть целым числом (int)
        chat_id = int(str(DB_CHANNEL_ID).replace('"', '').replace("'", "").strip())
        chat = await bot.get_chat(chat_id)
        pinned = chat.pinned_message
        
        # Читаем базу точь-в-точь как было в твоем оригинальном коде
        if pinned and pinned.text and "USERS_DB" in pinned.text:
            ids = pinned.text.split("\n")[1:]
            for uid in ids:
                if uid.strip().isdigit():
                    known_users.add(int(uid.strip()))
            print(f"✅ База данных загружена: {len(known_users)} пользователей.")
        else:
            print("❌ Закрепленное сообщение с базой 'USERS_DB' не найдено.")
    except Exception as e:
        print(f"❌ Ошибка загрузки БД: {e}")


async def sync_user_to_db(user_id: int):
    if user_id in known_users: return
    known_users.add(user_id)
    if not DB_CHANNEL_ID: return
    
    try:
        # Для приватных групп ID обязан быть целым числом (int)
        chat_id = int(str(DB_CHANNEL_ID).replace('"', '').replace("'", "").strip())
        chat = await bot.get_chat(chat_id)
        pinned = chat.pinned_message
        
        if pinned and pinned.text and "USERS_DB" in pinned.text:
            if str(user_id) not in pinned.text:
                new_text = pinned.text + f"\n{user_id}"
                if len(new_text) < 4000:
                    await bot.edit_message_text(chat_id=chat_id, message_id=pinned.message_id, text=new_text)
    except Exception as e:
        print(f"❌ Ошибка сохранения юзера: {e}")


# ================= ХЭНДЛЕРЫ =================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    # При старте пользователь автоматически добавляется в БД
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


# Работает и в группах (@dp.message), и в каналах (@dp.channel_post)
@dp.message(F.text == "/init_db")
@dp.channel_post(F.text == "/init_db")
async def init_db_in_channel(message: Message):
    chat_id = message.chat.id
    msg = await message.answer(f"USERS_DB:\n{ADMIN_ID}")
    await bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id) 
    await message.answer(f"✅ База данных успешно создана и закреплена!\nУбедись, что этот ID ({chat_id}) указан как `DB_CHANNEL_ID`.", parse_mode="Markdown")


@dp.message(F.text.startswith("/broadcast") | F.caption.startswith("/broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID: return 
    
    count = 0
    known_users_list = list(known_users) 
    
    if message.reply_to_message:
        for user_id in known_users_list:
            try:
                await message.reply_to_message.copy_to(chat_id=user_id)
                count += 1
            except Exception: pass
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


# ================= МИКРО-СЕРВЕР ДЛЯ RENDER =================
app = Flask(__name__)

@app.route('/')
def home(): 
    return "USM Bot is running on Render!"

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
    print("🚀 Бот запущен и готов к работе!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    start_web_server()
    asyncio.run(main())
