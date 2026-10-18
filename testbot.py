import asyncio
import datetime
import os
import threading
import aiohttp
from bs4 import BeautifulSoup
from flask import Flask
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

load_dotenv()

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7195495745  # Твой Telegram ID для рассылок
DB_CHANNEL_ID = os.getenv("DB_CHANNEL_ID") # Подтянется из Render после настройки

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище пользователей в оперативной памяти (для быстрой работы)
known_users = set()

class JournalState(StatesGroup):
    waiting_for_idnp_freq = State()
    waiting_for_idnp_eval = State()

# ================= ДАННЫЕ РАСПИСАНИЯ =================
TIMES = {1: "08:00-09:30", 2: "09:45-11:15", 3: "11:30-13:00", 4: "13:15-14:45", 5: "15:00-16:30"}

SCHEDULE = {
    "1": {
        "Понедельник": {
            1: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            2: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            3: {"all": {"subject": "История", "type": "Лекция", "teacher": "Александру Беженару", "room": "401/3"}},
            4: {"even": {"subject": "Химия", "type": "Лекция", "teacher": "Ала Фулга", "room": "127/3"}},
            5: {"odd": {"subject": "Химия", "type": "Семинар", "teacher": "Ала Фулга", "room": "433/3"}}
        },
        "Вторник": {
            1: {"all": {"subject": "Информатика", "type": "Лабораторная", "teacher": "Наталья Карчева", "room": "229/3"}},
            3: {
                "odd": {"subject": "Физика", "type": "Семинар", "teacher": "Виорел Дущак", "room": "427/BC"},
                "even": {"subject": "Биология", "type": "Семинар", "teacher": "В. Русу", "room": "527/3"}
            }
        },
        "Среда": {
            1: {"all": {"subject": "Английский язык", "type": "Семинар", "teacher": "Татьяна Цеплик", "room": "233/3"}},
            2: {"all": {"subject": "Английский язык", "type": "Семинар", "teacher": "Татьяна Цеплик", "room": "233/3"}},
            3: {
                "odd": {"subject": "Физика", "type": "Лекция", "teacher": "Виорел Дущак", "room": "425/4"},
                "even": {"subject": "Биология", "type": "Лекция", "teacher": "Вадим Русу", "room": "425/4"}
            },
            4: {"all": {"subject": "Математика", "type": "Лекция", "teacher": "Лиля Соловей", "room": "127"}},
            5: {"all": {"subject": "География", "type": "Лекция", "teacher": "Марчел Ревенко", "room": "401/3"}}
        },
        "Четверг": {
            1: {"all": {"subject": "География", "type": "Семинар", "teacher": "Марчел Ревенко", "room": "221/3"}},
            2: {"all": {"subject": "Математика", "type": "Семинар", "teacher": "Олег Топалэ", "room": "528/3"}},
            3: {"all": {"subject": "Русская литература", "type": "Лекция", "teacher": "Ольга Вулпе", "room": "127/3"}},
            4: {"all": {"subject": "Русский язык", "type": "Семинар", "teacher": "Ольга Вулпе", "room": "221/3"}}
        },
        "Пятница": {
            1: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            3: {"all": {"subject": "История", "type": "Семинар", "teacher": "Александру Беженару", "room": "433/3"}},
            4: {"all": {"subject": "Русский язык", "type": "Семинар", "teacher": "Ольга Вулпе", "room": "433/3"}}
        }
    },
    "2": {
        "Понедельник": {
            1: {"all": {"subject": "Английский язык", "type": "Семинар", "teacher": "Татьяна Цеплик", "room": "233/3"}},
            2: {"all": {"subject": "Английский язык", "type": "Семинар", "teacher": "Татьяна Цеплик", "room": "233/3"}},
            3: {"all": {"subject": "История", "type": "Лекция", "teacher": "Александру Беженару", "room": "401/3"}},
            4: {"even": {"subject": "Химия", "type": "Лекция", "teacher": "Ала Фулга", "room": "127/3"}}
        },
        "Вторник": {
            1: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            2: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            3: {"odd": {"subject": "Химия", "type": "Семинар", "teacher": "Ала Фулга", "room": "433/3"}},
            4: {"all": {"subject": "Русский язык", "type": "Семинар", "teacher": "Ольга Вулпе", "room": "433/3"}}
        },
        "Среда": {
            2: {"all": {"subject": "Информатика", "type": "Лабораторная", "teacher": "Наталья Карчева", "room": "229/3"}},
            3: {
                "odd": {"subject": "Физика", "type": "Лекция", "teacher": "Виорел Дущак", "room": "425/4"},
                "even": {"subject": "Биология", "type": "Лекция", "teacher": "Вадим Русу", "room": "425/4"}
            },
            4: {"all": {"subject": "Математика", "type": "Лекция", "teacher": "Лиля Соловей", "room": "127"}},
            5: {"all": {"subject": "География", "type": "Лекция", "teacher": "Марчел Ревенко", "room": "401/3"}}
        },
        "Четверг": {
            1: {"all": {"subject": "История", "type": "Семинар", "teacher": "Александру Беженару", "room": "527/3"}},
            2: {"all": {"subject": "География", "type": "Семинар", "teacher": "Марчел Ревенко", "room": "433/3"}},
            3: {"all": {"subject": "Русская литература", "type": "Лекция", "teacher": "Ольга Вулпе", "room": "127/3"}},
            4: {"odd": {"subject": "Биология", "type": "Семинар", "teacher": "В. Русу", "room": "527/3"}},
            5: {"all": {"subject": "Математика", "type": "Семинар", "teacher": "Лиля Соловей", "room": "528/3"}}
        },
        "Пятница": {
            2: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}}
        }
    },
    "3": {
        "Понедельник": {
            2: {"all": {"subject": "Английский язык", "type": "Семинар", "teacher": "Марчела Калкей", "room": "527/3"}},
            3: {"all": {"subject": "История", "type": "Лекция", "teacher": "Александру Беженару", "room": "401/3"}},
            4: {
                "odd": {"subject": "Физика", "type": "Семинар", "teacher": "Виорел Дущак", "room": "433/3"},
                "even": {"subject": "Химия", "type": "Лекция", "teacher": "Ала Фулга", "room": "127/3"}
            },
            5: {"even": {"subject": "Химия", "type": "Семинар", "teacher": "Ала Фулга", "room": "433/3"}}
        },
        "Вторник": {
            2: {"all": {"subject": "Информатика", "type": "Лабораторная", "teacher": "Наталья Карчева", "room": "229/3"}},
            3: {
                "odd": {"subject": "Биология", "type": "Семинар", "teacher": "В. Русу", "room": "527/3"},
                "even": {"subject": "Физика", "type": "Семинар", "teacher": "Виорел Дущак", "room": "433/3"}
            },
            4: {"all": {"subject": "История", "type": "Семинар", "teacher": "Александру Беженару", "room": "527/3"}}
        },
        "Среда": {
            1: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            2: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            3: {
                "odd": {"subject": "Физика", "type": "Лекция", "teacher": "Виорел Дущак", "room": "425/4"},
                "even": {"subject": "Биология", "type": "Лекция", "teacher": "Вадим Русу", "room": "425/4"}
            },
            4: {"all": {"subject": "Математика", "type": "Лекция", "teacher": "Лиля Соловей", "room": "127"}},
            5: {"all": {"subject": "География", "type": "Лекция", "teacher": "Марчел Ревенко", "room": "401/3"}}
        },
        "Четверг": {
            3: {"all": {"subject": "Русская литература", "type": "Лекция", "teacher": "Ольга Вулпе", "room": "127/3"}},
            4: {"all": {"subject": "Математика", "type": "Семинар", "teacher": "Лиля Соловей", "room": "528/3"}},
            5: {"all": {"subject": "Русский язык", "type": "Семинар", "teacher": "Ольга Вулпе", "room": "221/3"}}
        },
        "Пятница": {
            1: {"all": {"subject": "Русский язык", "type": "Семинар", "teacher": "Ольга Вулпе", "room": "527/3"}},
            3: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            4: {"all": {"subject": "Английский язык", "type": "Семинар", "teacher": "Марчела Калкей", "room": "233/3"}}
        }
    },
    "4": {
        "Понедельник": {
            2: {"all": {"subject": "Информатика", "type": "Лабораторная", "teacher": "Наталья Карчева", "room": "231/3"}},
            3: {"all": {"subject": "История", "type": "Лекция", "teacher": "Александру Беженару", "room": "401/3"}},
            4: {"even": {"subject": "Химия", "type": "Лекция", "teacher": "Ала Фулга", "room": "127/3"}}
        },
        "Вторник": {
            1: {"all": {"subject": "Английский язык", "type": "Семинар", "teacher": "Татьяна Цеплик", "room": "233/3"}},
            2: {"all": {"subject": "Английский язык", "type": "Семинар", "teacher": "Татьяна Цеплик", "room": "233/3"}},
            3: {"even": {"subject": "Физика", "type": "Семинар", "teacher": "Виорел Дущак", "room": "433/3"}}
        },
        "Среда": {
            3: {
                "odd": {"subject": "Физика", "type": "Лекция", "teacher": "Виорел Дущак", "room": "425/4"},
                "even": {"subject": "Биология", "type": "Лекция", "teacher": "Вадим Русу", "room": "425/4"}
            },
            4: {"all": {"subject": "Математика", "type": "Лекция", "teacher": "Лиля Соловей", "room": "127"}},
            5: {"all": {"subject": "География", "type": "Лекция", "teacher": "Марчел Ревенко", "room": "401/3"}}
        },
        "Четверг": {
            1: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            2: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}},
            3: {"all": {"subject": "Русская литература", "type": "Лекция", "teacher": "Ольга Вулпе", "room": "127/3"}}
        },
        "Пятница": {
            1: {"all": {"subject": "География", "type": "Семинар", "teacher": "Марчел Ревенко", "room": "221/3"}},
            2: {"all": {"subject": "Русский язык", "type": "Семинар", "teacher": "Ольга Вулпе", "room": "433/3"}},
            4: {"all": {"subject": "Румынский язык", "type": "Семинар", "teacher": "Лилия Долган", "room": "521/3"}}
        }
    }
}

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
                if len(new_text) < 4000: # Защита от лимитов Telegram
                    await bot.edit_message_text(chat_id=DB_CHANNEL_ID, message_id=pinned.message_id, text=new_text)
    except Exception as e:
        print(f"❌ Ошибка сохранения юзера: {e}")

# ================= ЛОГИКА ПОГОДЫ (OpenWeather) =================
OW_API_KEY = "10ee9c368fc7dc64b18dae5c7a963d28"
LAT, LON = 47.0105, 28.8638

# Эмодзи по кодам иконок OpenWeather (день/ночь)
OW_EMOJIS = {
    "01d": "☀️", "01n": "🌙",
    "02d": "🌤", "02n": "🌤",
    "03d": "☁️", "03n": "☁️",
    "04d": "⛅️", "04n": "⛅️",
    "09d": "🌧", "09n": "🌧",
    "10d": "🌦", "10n": "🌦",
    "11d": "⛈", "11n": "⛈",
    "13d": "❄️", "13n": "❄️",
    "50d": "🌫", "50n": "🌫"
}

async def get_weather_today():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={OW_API_KEY}&units=metric&lang=ru"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200: 
                return "❌ Не удалось получить данные о погоде."
            data = await response.json()
            
            temp = round(data["main"]["temp"])
            feels_like = round(data["main"]["feels_like"])
            desc = data["weather"][0]["description"].capitalize()
            icon = data["weather"][0]["icon"]
            emoji = OW_EMOJIS.get(icon, "❓")
            
            return f"🌤 Погода в Кишиневе сейчас:\n\n🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n{emoji} На улице: {desc}"

async def get_weather_week():
    # Стандартный бесплатный API дает прогноз на 5 дней (каждые 3 часа)
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={OW_API_KEY}&units=metric&lang=ru"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200: 
                return "❌ Не удалось получить прогноз."
            data = await response.json()
            
            daily_data = {}
            # Группируем 3-часовые прогнозы по дням
            for item in data["list"]:
                date_str = item["dt_txt"].split(" ")[0]
                temp = item["main"]["temp"]
                
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        "min_temp": temp,
                        "max_temp": temp,
                        "desc": item["weather"][0]["description"].capitalize(),
                        "icon": item["weather"][0]["icon"]
                    }
                else:
                    daily_data[date_str]["min_temp"] = min(daily_data[date_str]["min_temp"], temp)
                    daily_data[date_str]["max_temp"] = max(daily_data[date_str]["max_temp"], temp)
                    # Выбираем описание примерно на середину дня (около 12:00 - 15:00)
                    if "12:00:00" in item["dt_txt"] or "15:00:00" in item["dt_txt"]:
                        daily_data[date_str]["desc"] = item["weather"][0]["description"].capitalize()
                        daily_data[date_str]["icon"] = item["weather"][0]["icon"]

            forecast_text = "📅 Прогноз в Кишиневе на 5 дней:\n\n"
            # OpenWeather выдает максимум 5 дней в бесплатном тарифе
            for date_str, info in list(daily_data.items())[:5]:
                formatted_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m")
                min_temp, max_temp = round(info["min_temp"]), round(info["max_temp"])
                emoji = OW_EMOJIS.get(info["icon"], "")
                forecast_text += f"🔹 {formatted_date}: от {min_temp}°C до {max_temp}°C, {emoji} {info['desc']}\n"
            
            return forecast_text
# ================= АВТОРИЗАЦИЯ НА САЙТЕ USM =================
async def login_to_usm(session, idnp: str):
    url = "https://studentcrd.usm.md/"
    try:
        async with session.get(url, timeout=10) as get_response:
            if get_response.status != 200:
                return None, "❌ Ошибка подключения к сайту USM."
            
            soup = BeautifulSoup(await get_response.text(), 'html.parser')
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
            eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})
            
            if not viewstate or not eventvalidation:
                return None, "❌ Не удалось получить токены безопасности страницы."
            
            payload = {
                '__VIEWSTATE': viewstate.get('value', ''),
                '__VIEWSTATEGENERATOR': viewstategenerator.get('value', '') if viewstategenerator else '',
                '__EVENTVALIDATION': eventvalidation.get('value', ''),
                'txtCodperson': idnp,
                'btLogin': 'Login'
            }
            
        async with session.post(url, data=payload, timeout=10) as post_response:
            if post_response.status != 200:
                return None, "❌ Ошибка при отправке данных авторизации."
            
            result_soup = BeautifulSoup(await post_response.text(), 'html.parser')
            error_span = result_soup.find('span', {'id': 'lbErr'})
            if error_span and error_span.text.strip():
                return None, f"❌ Ошибка входа: {error_span.text.strip()}"
            
            return result_soup, None
    except Exception as e:
        return None, f"❌ Ошибка обработки данных: {e}"

# ================= ЛОГИКА ЭЛЕКТРОННОГО ЖУРНАЛА (ПОСЕЩАЕМОСТЬ) =================
async def fetch_journal_absences(idnp: str) -> str:
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        result_soup, error = await login_to_usm(session, idnp)
        if error: return error
        
        freq_div = result_soup.find('div', id='divNoteBysemest')
        if not freq_div or not freq_div.find('table'):
            return "❌ Не удалось найти раздел с посещаемостью."
        
        table = freq_div.find('table')
        attendance_dict = {}
        current_subject = "Неизвестный предмет"
        current_teacher = "Неизвестный преподаватель"
        
        for row in table.find_all('tr'):
            tds = row.find_all('td')
            if not tds: continue
                
            if len(tds) == 1 and tds[0].get('colspan') == '3':
                b_tag = tds[0].find('b')
                if b_tag:
                    subj_text = b_tag.text.strip()
                    if "semestru" not in subj_text.lower() and "ac" not in subj_text.lower():
                        current_subject = subj_text
                        current_teacher = "" 
                        
            elif len(tds) == 2:
                teacher_b = tds[1].find('b')
                current_teacher = teacher_b.text.strip() if teacher_b else tds[1].text.strip()
                
            elif len(tds) == 3:
                raw_date = tds[1].text.strip()
                mark = tds[2].text.strip().lower() 
                
                date_parts = raw_date.split(' ')[0].split('.')
                short_date = f"{date_parts[0]}.{date_parts[1]}" if len(date_parts) >= 2 else raw_date
                
                key = f"📖 <b>{current_subject}</b>\n👨‍🏫 <i>{current_teacher}</i>"
                if key not in attendance_dict: attendance_dict[key] = []
                    
                if mark == 'a':
                    attendance_dict[key].append(f"❌ {short_date}")
                elif mark == '':
                    attendance_dict[key].append(f"✅ {short_date}")
                else:
                    attendance_dict[key].append(f"💭 Оценка: {mark}, {short_date}")
        
        if not attendance_dict: return "Данные о посещаемости отсутствуют."
        
        final_text = "📊 <b>Посещаемость и баллы:</b>\n\n"
        for subj_header, logs in attendance_dict.items():
            final_text += f"{subj_header}\n" + " | ".join(logs) + "\n\n"
            
        return final_text[:4000] + ("\n..." if len(final_text) > 4000 else "")

# ================= ЛОГИКА ОЦЕНОК ЗА ТЕСТЫ =================
async def fetch_journal_evaluare(idnp: str) -> str:
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        result_soup, error = await login_to_usm(session, idnp)
        if error: return error
        
        eval_div = result_soup.find('div', id='divEvaluareCur')
        if not eval_div or not eval_div.find('table'):
            return "❌ Не удалось найти раздел с оценками."
        
        table = eval_div.find('table')
        eval_text = "📝 <b>Ваши оценки за тесты:</b>\n\n"
        current_subject = ""
        current_teacher = ""
        
        for row in table.find_all('tr'):
            tds = row.find_all('td')
            if not tds or len(tds) < 2: continue
            
            if 'w-50' in tds[0].get('class', []) or tds[0].find('b'):
                current_subject = tds[0].text.strip()
                current_teacher = tds[1].text.strip()
            else:
                test_name = tds[0].text.strip()
                grade = tds[1].text.strip()
                if test_name and grade:
                    eval_text += f"📖 <b>{current_subject}</b>\n👨‍🏫 <i>{current_teacher}</i>\n📌 Тест: {test_name}\n💭 Оценка: <b>{grade}</b>\n\n"
                    
        if eval_text == "📝 <b>Ваши оценки за тесты:</b>\n\n":
            return "Данные об оценках отсутствуют."
            
        return eval_text[:4000]

# ================= ЛОГИКА РАСПИСАНИЯ =================
def get_current_week_info():
    now = datetime.datetime.now()
    if now.weekday() >= 5: target_date = now.date() + datetime.timedelta(days=(7 - now.weekday()))
    else: target_date = now.date()
    start_date = datetime.date(2026, 9, 21)
    if target_date < start_date: target_date = start_date
    return "even" if ((target_date - start_date).days // 7) % 2 != 0 else "odd"

def format_day_schedule(group_id, subgroup_id, day):
    week_type = get_current_week_info()
    week_label = "Четная" if week_type == "even" else "Нечетная"
    text = f"🎓 Группа {group_id} | 👥 Подгруппа {subgroup_id} | 📅 {day}\n🗓 Неделя: {week_label}\n\n"
    active_lessons = {}
    
    for pair_num, variations in SCHEDULE[str(subgroup_id)].get(day, {}).items():
        if "all" in variations: active_lessons[pair_num] = variations["all"]
        elif week_type in variations: active_lessons[pair_num] = variations[week_type]
            
    if not active_lessons: return text + "В этот день пар нет! 🎉 Выходной."
        
    for pair_num in range(min(active_lessons.keys()), max(active_lessons.keys()) + 1):
        time_str = TIMES.get(pair_num, "")
        if pair_num in active_lessons:
            l = active_lessons[pair_num]
            text += f"{pair_num}. 🕒 {time_str}\n📚 {l['subject']} ({l['type']})\n👨‍🏫 {l['teacher']}\n🚪 Аудитория: {l['room']}\n\n"
        else:
            text += f"{pair_num}. 🕒 {time_str}\n🪟 Окно (свободная пара)\n\n"
    return text.strip()

# ================= КЛАВИАТУРЫ =================
def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Группа 1", callback_data="group_1"), 
         InlineKeyboardButton(text="🎓 Группа 2", callback_data="group_2"),
         InlineKeyboardButton(text="🎓 Группа 3", callback_data="group_3")],
        [InlineKeyboardButton(text="🌤 Погода", callback_data="weather_today"), 
         InlineKeyboardButton(text="📅 Прогноз", callback_data="weather_week")],
        [InlineKeyboardButton(text="📖 Журнал (Оценки и Пропуски)", callback_data="open_journal_freq")],
        [InlineKeyboardButton(text="📝 Журнал: Оценки за Тесты", callback_data="open_journal_eval")]
    ])

def get_subgroups_kb(group_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Подгруппа 1", callback_data=f"subgroup_{group_id}_1"),
         InlineKeyboardButton(text="👥 Подгруппа 2", callback_data=f"subgroup_{group_id}_2")],
        [InlineKeyboardButton(text="👥 Подгруппа 3", callback_data=f"subgroup_{group_id}_3"),
         InlineKeyboardButton(text="👥 Подгруппа 4", callback_data=f"subgroup_{group_id}_4")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])

def get_days_kb(group_id, subgroup_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ПН", callback_data=f"day_{group_id}_{subgroup_id}_Понедельник"),
         InlineKeyboardButton(text="ВТ", callback_data=f"day_{group_id}_{subgroup_id}_Вторник"),
         InlineKeyboardButton(text="СР", callback_data=f"day_{group_id}_{subgroup_id}_Среда"),
         InlineKeyboardButton(text="ЧТ", callback_data=f"day_{group_id}_{subgroup_id}_Четверг"),
         InlineKeyboardButton(text="ПТ", callback_data=f"day_{group_id}_{subgroup_id}_Пятница")],
        [InlineKeyboardButton(text="🔙 К выбору подгруппы", callback_data=f"group_{group_id}")]
    ])

# ================= ХЭНДЛЕРЫ =================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await sync_user_to_db(message.from_user.id) # Добавляем юзера в БД канала
    await state.clear()
    await message.answer("🏛 Добро пожаловать в расписание USM!\n\nВыберите нужный раздел из меню:", reply_markup=get_main_kb())

# --- Первоначальная настройка Базы Данных ---
@dp.channel_post(F.text == "/init_db")
async def init_db_in_channel(message: Message):
    channel_id = message.chat.id
    msg = await message.answer(f"USERS_DB:\n{ADMIN_ID}") # Создаем сообщение с твоим ID
    await bot.pin_chat_message(chat_id=channel_id, message_id=msg.message_id) # Закрепляем его
    await message.answer(
        f"✅ База данных успешно создана и закреплена!\n\n"
        f"Зайди на Render.com, открой настройки проекта (Environment) и добавь новую переменную:\n"
        f"Ключ: `DB_CHANNEL_ID`\n"
        f"Значение: `{channel_id}`", parse_mode="Markdown"
    )

# --- Команда для админской рассылки ---
@dp.message(F.text.startswith("/broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID: return 
    
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        await message.answer("⚠️ Введите текст для рассылки.\nПример: `/broadcast Всем привет!`", parse_mode="Markdown")
        return
        
    count = 0
    for user_id in list(known_users):
        try:
            await bot.send_message(user_id, f"📢 <b>Оповещение:</b>\n\n{text_to_send}", parse_mode="HTML")
            count += 1
        except Exception: pass 
            
    await message.answer(f"✅ Рассылка завершена! Отправлено {count} пользователям.")

# --- Хэндлеры журнала ---
@dp.callback_query(F.data.in_(["open_journal_freq", "open_journal_eval"]))
async def ask_idnp(callback: CallbackQuery, state: FSMContext):
    if callback.data == "open_journal_freq": await state.set_state(JournalState.waiting_for_idnp_freq)
    else: await state.set_state(JournalState.waiting_for_idnp_eval)
        
    await callback.message.edit_text(
        text="Введите ваш IDNP (Задняя часть паспорта).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="back_main")]])
    )
    await callback.answer()

@dp.message(JournalState.waiting_for_idnp_freq)
async def process_idnp_freq(message: Message, state: FSMContext):
    await sync_user_to_db(message.from_user.id)
    idnp = message.text.strip()
    if not idnp.isdigit() or len(idnp) != 13:
        await message.answer("⚠️ Неверный формат. IDNP должен состоять ровно из 13 цифр.")
        return
    wait_msg = await message.answer("⏳ Загружаю посещаемость...")
    result = await fetch_journal_absences(idnp)
    await state.clear()
    await wait_msg.edit_text(result, reply_markup=get_main_kb(), parse_mode="HTML")

@dp.message(JournalState.waiting_for_idnp_eval)
async def process_idnp_eval(message: Message, state: FSMContext):
    await sync_user_to_db(message.from_user.id)
    idnp = message.text.strip()
    if not idnp.isdigit() or len(idnp) != 13:
        await message.answer("⚠️ Неверный формат. IDNP должен состоять ровно из 13 цифр.")
        return
    wait_msg = await message.answer("⏳ Загружаю оценки за тесты...")
    result = await fetch_journal_evaluare(idnp)
    await state.clear()
    await wait_msg.edit_text(result, reply_markup=get_main_kb(), parse_mode="HTML")

# --- Хэндлеры расписания ---
@dp.callback_query(F.data.startswith("group_"))
async def select_group(callback: CallbackQuery):
    group_id = callback.data.split("_")[1]
    await callback.message.edit_text(
        text=f"🎓 Вы выбрали Группу {group_id}.\n\nПожалуйста, выберите вашу подгруппу:",
        reply_markup=get_subgroups_kb(group_id)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("subgroup_"))
async def select_subgroup(callback: CallbackQuery):
    parts = callback.data.split("_")
    group_id, subgroup_id = parts[1], parts[2]
    day = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Понедельник", "Понедельник"][datetime.datetime.now().weekday()]
    await callback.message.edit_text(text=format_day_schedule(group_id, subgroup_id, day), reply_markup=get_days_kb(group_id, subgroup_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("day_"))
async def select_day(callback: CallbackQuery):
    parts = callback.data.split("_")
    group_id, subgroup_id, day = parts[1], parts[2], parts[3]
    try: await callback.message.edit_text(text=format_day_schedule(group_id, subgroup_id, day), reply_markup=get_days_kb(group_id, subgroup_id))
    except Exception: pass 
    await callback.answer()

@dp.callback_query(F.data == "weather_today")
async def show_weather_today(callback: CallbackQuery):
    await callback.message.edit_text(text=await get_weather_today(), reply_markup=get_main_kb())
    await callback.answer()

@dp.callback_query(F.data == "weather_week")
async def show_weather_week(callback: CallbackQuery):
    await callback.message.edit_text(text=await get_weather_week(), reply_markup=get_main_kb())
    await callback.answer()

@dp.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear() 
    await callback.message.edit_text(text="🏛 Расписание USM\n\nВыберите раздел:", reply_markup=get_main_kb())
    await callback.answer()

# ================= МИКРО-СЕРВЕР ДЛЯ RENDER =================
app = Flask(__name__)

@app.route('/')
def home(): return "USM Bot is running!"

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
    await load_db_from_channel() # Загружаем БД перед стартом
    await dp.start_polling(bot)

if __name__ == "__main__":
    start_web_server()
    asyncio.run(main())
