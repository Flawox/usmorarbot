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

# Подгружаем переменные из .env файла
load_dotenv()

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class JournalState(StatesGroup):
    waiting_for_idnp = State()

# ================= ДАННЫЕ РАСПИСАНИЯ =================
TIMES = {1: "08:00-09:30", 2: "09:45-11:15", 3: "11:30-13:00", 4: "13:15-14:45", 5: "15:00-16:30"}

# В словаре ключи 1, 2, 3, 4 соответствуют ПОДГРУППАМ, так как расписание зависит от подгруппы
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

# ================= ЛОГИКА ПОГОДЫ =================
LAT, LON = 47.0105, 28.8638
WEATHER_CODES = {
    0: "Ясно ☀️", 1: "Преимущественно ясно 🌤", 2: "Переменная облачность ⛅️", 3: "Пасмурно ☁️",
    45: "Туман 🌫", 48: "Иней 🌫",
    51: "Легкая морось 🌧", 53: "Умеренная морось 🌧", 55: "Густая морось 🌧",
    61: "Слабый дождь 🌧", 63: "Умеренный дождь 🌧", 65: "Сильный дождь 🌧",
    71: "Слабый снег ❄️", 73: "Умеренный снег ❄️", 75: "Сильный снег ❄️",
    80: "Слабый ливень 🌦", 81: "Умеренный ливень 🌧", 82: "Сильный ливень ⛈",
    95: "Гроза ⛈", 96: "Гроза с градом ⛈", 99: "Сильная гроза ⛈"
}

async def get_weather_today():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,apparent_temperature,weather_code&timezone=Europe%2FChisinau"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200: return "❌ Не удалось получить данные о погоде."
            data = await response.json()
            temp, feels_like = round(data["current"]["temperature_2m"]), round(data["current"]["apparent_temperature"])
            desc = WEATHER_CODES.get(data["current"]["weather_code"], "Неизвестно ❓")
            return f"🌤 Погода в Кишиневе сейчас:\n\n🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n☁️ На улице: {desc}"

async def get_weather_week():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe%2FChisinau"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200: return "❌ Не удалось получить прогноз."
            data = await response.json()
            forecast_text = "📅 Прогноз в Кишиневе на 7 дней:\n\n"
            for i in range(7):
                formatted_date = datetime.datetime.strptime(data["daily"]["time"][i], "%Y-%m-%d").strftime("%d.%m")
                min_temp, max_temp = round(data["daily"]["temperature_2m_min"][i]), round(data["daily"]["temperature_2m_max"][i])
                desc = WEATHER_CODES.get(data["daily"]["weather_code"][i], "Неизвестно")
                forecast_text += f"🔹 {formatted_date}: от {min_temp}°C до {max_temp}°C, {desc}\n"
            return forecast_text

async def fetch_journal_absences(idnp: str) -> str:
    url = "https://studentcrd.usm.md/"
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get(url, timeout=10) as get_response:
                if get_response.status != 200:
                    return "❌ Ошибка подключения к сайту USM при попытке входа."
                
                soup = BeautifulSoup(await get_response.text(), 'html.parser')
                viewstate = soup.find('input', {'name': '__VIEWSTATE'})
                viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
                eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})
                
                if not viewstate or not eventvalidation:
                    return "❌ Не удалось получить токены безопасности страницы."
                
                payload = {
                    '__VIEWSTATE': viewstate.get('value', ''),
                    '__VIEWSTATEGENERATOR': viewstategenerator.get('value', '') if viewstategenerator else '',
                    '__EVENTVALIDATION': eventvalidation.get('value', ''),
                    'txtCodperson': idnp,
                    'btLogin': 'Login'
                }
                
            async with session.post(url, data=payload, timeout=10) as post_response:
                if post_response.status != 200:
                    return "❌ Ошибка при отправке данных авторизации."
                
                result_soup = BeautifulSoup(await post_response.text(), 'html.parser')
                
                error_span = result_soup.find('span', {'id': 'lbErr'})
                if error_span and error_span.text.strip():
                    return f"❌ Ошибка входа: {error_span.text.strip()}"
                
                freq_div = result_soup.find('div', id='divNoteBysemest')
                if not freq_div or not freq_div.find('table'):
                    return "❌ Не удалось найти раздел с посещаемостью или таблица пуста."
                
                table = freq_div.find('table')
                attendance_dict = {}
                current_subject = "Неизвестный предмет"
                current_teacher = "Неизвестный преподаватель"
                
                for row in table.find_all('tr'):
                    tds = row.find_all('td')
                    if not tds:
                        continue
                        
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
                        mark = tds[2].text.strip().lower() # Здесь либо пустота, либо "a", либо оценка
                        
                        date_parts = raw_date.split(' ')[0].split('.')
                        short_date = f"{date_parts[0]}.{date_parts[1]}" if len(date_parts) >= 2 else raw_date
                        
                        key = f"📖 {current_subject}\n👨‍‍🏫 {current_teacher}"
                        if key not in attendance_dict:
                            attendance_dict[key] = []
                            
                        # Проверяем значение в 3-й колонке
                        if mark == 'a':
                            attendance_dict[key].append(f"❌ {short_date}")
                        elif mark == '':
                            attendance_dict[key].append(f"✅ {short_date}")
                        else:
                            # Если там не "a" и не пусто — значит стоит оценка
                            attendance_dict[key].append(f"💭 Оценка: {mark}, {short_date}")
                
                if not attendance_dict:
                    return "Данные о посещаемости и оценках отсутствуют."
                
                final_text = "📊 Ваши оценки и посещаемость:\n\n"
                for subj_header, logs in attendance_dict.items():
                    final_text += f"{subj_header}\n" + " | ".join(logs) + "\n\n"
                    
                if len(final_text) > 4000:
                    final_text = final_text[:4000] + "\n... (данные обрезаны)"
                    
                return final_text
                
        except Exception as e:
            return f"❌ Произошла ошибка при обработке данных: {e}"

# ================= ЛОГИКА РАСПИСАНИЯ =================
def get_current_week_info():
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        target_date = now.date() + datetime.timedelta(days=(7 - now.weekday()))
    else:
        target_date = now.date()
    start_date = datetime.date(2026, 9, 21)
    if target_date < start_date: target_date = start_date
    return "even" if ((target_date - start_date).days // 7) % 2 != 0 else "odd"

def format_day_schedule(group_id, subgroup_id, day):
    week_type = get_current_week_info()
    week_label = "Четная" if week_type == "even" else "Нечетная"
    text = f"🎓 Группа {group_id} | 👥 Подгруппа {subgroup_id} | 📅 {day}\n🗓 Неделя: {week_label}\n\n"
    active_lessons = {}
    
    # Берем расписание строго по номеру подгруппы
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
        [InlineKeyboardButton(text="📖 Электронный журнал (Оценки и Пропуски)", callback_data="open_journal")]
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
    await state.clear()
    await message.answer("🏛 Добро пожаловать в расписание USM!\n\nВыберите нужный раздел из меню:", reply_markup=get_main_kb())

@dp.callback_query(F.data == "open_journal")
async def ask_idnp(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JournalState.waiting_for_idnp)
    await callback.message.edit_text(
        text="Введите ваш IDNP (Задняя часть паспорта).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="back_main")]])
    )
    await callback.answer()

@dp.message(JournalState.waiting_for_idnp)
async def process_idnp(message: Message, state: FSMContext):
    idnp = message.text.strip()
    if not idnp.isdigit() or len(idnp) != 13:
        await message.answer("⚠️ Неверный формат. IDNP должен состоять ровно из 13 цифр. Попробуйте еще раз или нажмите /start.")
        return
    wait_msg = await message.answer("⏳ Подключаюсь к журналу USM, загружаю данные...")
    result = await fetch_journal_absences(idnp)
    await state.clear()
    
    await wait_msg.edit_text(result, reply_markup=get_main_kb(), parse_mode="HTML")

# --- Обработка выбора группы ---
@dp.callback_query(F.data.startswith("group_"))
async def select_group(callback: CallbackQuery):
    group_id = callback.data.split("_")[1]
    await callback.message.edit_text(
        text=f"🎓 Вы выбрали Группу {group_id}.\n\nПожалуйста, выберите вашу подгруппу:",
        reply_markup=get_subgroups_kb(group_id)
    )
    await callback.answer()

# --- Обработка выбора подгруппы ---
@dp.callback_query(F.data.startswith("subgroup_"))
async def select_subgroup(callback: CallbackQuery):
    parts = callback.data.split("_")
    group_id = parts[1]
    subgroup_id = parts[2]
    
    day = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Понедельник", "Понедельник"][datetime.datetime.now().weekday()]
    
    await callback.message.edit_text(
        text=format_day_schedule(group_id, subgroup_id, day), 
        reply_markup=get_days_kb(group_id, subgroup_id)
    )
    await callback.answer()

# --- Обработка выбора дня недели ---
@dp.callback_query(F.data.startswith("day_"))
async def select_day(callback: CallbackQuery):
    parts = callback.data.split("_")
    group_id = parts[1]
    subgroup_id = parts[2]
    day = parts[3]
    try: 
        await callback.message.edit_text(
            text=format_day_schedule(group_id, subgroup_id, day), 
            reply_markup=get_days_kb(group_id, subgroup_id)
        )
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

# ================= ЗАПУСК =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    start_web_server()
    asyncio.run(main())
