import asyncio
import os
import threading

from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message


BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Добавь BOT_TOKEN в переменные окружения Render.")

dp = Dispatcher()
app = Flask(__name__)


@dp.message(Command("pdfid"))
async def get_pdf_id(message: Message):
    document = message.document

    if document is None and message.reply_to_message:
        document = message.reply_to_message.document

    if document is None:
        await message.answer(
            "Ответь командой /pdfid на сообщение с PDF-файлом."
        )
        return

    is_pdf = (
        document.mime_type == "application/pdf"
        or (document.file_name or "").lower().endswith(".pdf")
    )

    if not is_pdf:
        await message.answer("Нужен файл в формате PDF.")
        return

    await message.answer(document.file_id, parse_mode=None)


@app.route("/")
def home():
    return "OK"


def run_web():
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        use_reloader=False,
    )


async def main():
    async with Bot(token=BOT_TOKEN) as bot:
        await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
