import telebot
import sqlite3
import os
from datetime import datetime, timedelta
from telebot import types
from Utils.Utils import verifyPassword

dbDir = "C:/Users/alexa/Desktop/KSU-Assistant-after-venv/Utils"
DATABASE_PATH = os.path.join(dbDir, "university.db")
botToken = '7637461107:AAFH6C5oy9WZIuQhZfkmH6YUbVNseduRA90'
bot = telebot.TeleBot(botToken)
user_states = {}

def getDBConnection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Функция для отображения главного меню
def send_main_menu(chat_id):
    conn = getDBConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT silent_mode FROM users WHERE telegram_id = ?", (chat_id,))
    user = cursor.fetchone()
    conn.close()

    silent_mode = user['silent_mode'] if user else 0
    silent_text = "🔕 Включить" if not silent_mode else "🔔 Выключить"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    schedule_btn = types.KeyboardButton("📅 Получить расписание")
    events_btn = types.KeyboardButton("📋 Мероприятия")
    silent_btn = types.KeyboardButton(silent_text)
    markup.add(schedule_btn, events_btn, silent_btn)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

# /start
@bot.message_handler(commands=['start'])
def handleStart(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)

    conn = getDBConnection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (chat_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        send_main_menu(chat_id)
        bot.send_message(chat_id, "Вы уже авторизованы!")
    else:
        markup = types.InlineKeyboardMarkup()
        login_button = types.InlineKeyboardButton(text="🔐 Авторизоваться", callback_data="start_login")
        markup.add(login_button)
        bot.send_message(
            chat_id,
            "👋 Привет! Я твой ассистент в KSU.\n\nДля использования всех функций, пожалуйста, авторизуйся.",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == "start_login")
def start_login_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    bot.send_message(chat_id, 'Введите вашу корпоративную почту (например, @studklg.ru или @tksu.ru):')
    user_states[chat_id] = {'state': 'WAIT_EMAIL'}

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('state') == 'WAIT_EMAIL')
def handle_email(message):
    chat_id = message.chat.id
    email = message.text.strip()

    if not (email.endswith('@studklg.ru') or email.endswith('@tksu.ru')):
        bot.send_message(chat_id, 'Неподдерживаемый домен почты. Используйте @studklg.ru или @tksu.ru.')
        return

    conn = getDBConnection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        bot.send_message(chat_id, 'Пользователь с такой почтой не найден.')
        return

    if user['telegram_id'] is not None:
        if str(user['telegram_id']) == str(chat_id):
            bot.send_message(chat_id, 'Вы уже авторизованы.')
        else:
            bot.send_message(chat_id, 'Этот email уже привязан к другому аккаунту.')
        user_states.pop(chat_id, None)
        return

    user_states[chat_id] = {'state': 'WAIT_PASSWORD', 'email': email}
    bot.send_message(chat_id, 'Введите пароль:')

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('state') == 'WAIT_PASSWORD')
def handle_password(message):
    chat_id = message.chat.id
    password = message.text.strip()
    email = user_states[chat_id]['email']

    conn = getDBConnection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()

    if not user or not verifyPassword(user['password_hash'], password):
        bot.send_message(chat_id, 'Ошибка авторизации. Попробуйте сначала /start')
        conn.close()
        user_states.pop(chat_id, None)
        return

    cursor.execute('UPDATE users SET telegram_id = ? WHERE email = ?', (chat_id, email))
    conn.commit()
    conn.close()

    bot.send_message(chat_id, f'✅ Успешно авторизованы как {user["role"]}.')
    user_states.pop(chat_id, None)
    send_main_menu(chat_id)

# Обработчик кнопки "Получить расписание"
@bot.message_handler(func=lambda m: m.text == "📅 Получить расписание")
def show_schedule_options(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    today_btn = types.KeyboardButton("📆 Сегодня")
    week_btn = types.KeyboardButton("🗓️ На неделю")
    back_btn = types.KeyboardButton("🔙 Назад")
    markup.add(today_btn, week_btn, back_btn)
    bot.send_message(message.chat.id, "Выберите, за какой период показать расписание:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def handle_back(message):
    send_main_menu(message.chat.id)

# Показ расписания
@bot.message_handler(func=lambda m: m.text in ["📆 Сегодня", "🗓️ На неделю"])
def handle_schedule_period(message):
    chat_id = message.chat.id
    mode = 'today' if message.text == "📆 Сегодня" else 'week'

    conn = getDBConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (chat_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        bot.send_message(chat_id, "❌ Вы не авторизованы.")
        return

    user_id = user["id"]
    schedule_text = fetch_schedule(user_id, mode)
    bot.send_message(chat_id, schedule_text, parse_mode="HTML")

def fetch_schedule(user_id, mode='today'):
    conn = getDBConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT group_id FROM students WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "❌ Вы не являетесь студентом или не назначены в группу."

    group_id = row["group_id"]
    today = datetime.today()
    weekday = today.weekday()
    today_str = today.strftime('%Y-%m-%d')

    if mode == 'today':
        cursor.execute("""
            SELECT lessons.weekday, lessons.pair_number, pair_times.start_time, pair_times.end_time,
                   subjects.name AS subject_name, rooms.room_number, rooms.building
            FROM lessons
            JOIN pair_times ON lessons.pair_number = pair_times.pair_number
            JOIN subjects ON lessons.subject_id = subjects.id
            JOIN rooms ON lessons.room_id = rooms.id
            WHERE lessons.group_id = ? AND lessons.weekday = ?
              AND date(?) BETWEEN date(lessons.start_date) AND date(lessons.end_date)
            ORDER BY lessons.pair_number
        """, (group_id, weekday, today_str))
    else:
        week_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        weekday_range = tuple(i for i in range(7))
        cursor.execute(f"""
            SELECT lessons.weekday, lessons.pair_number, pair_times.start_time, pair_times.end_time,
                   subjects.name AS subject_name, rooms.room_number, rooms.building
            FROM lessons
            JOIN pair_times ON lessons.pair_number = pair_times.pair_number
            JOIN subjects ON lessons.subject_id = subjects.id
            JOIN rooms ON lessons.room_id = rooms.id
            WHERE lessons.group_id = ?
              AND lessons.weekday IN ({','.join(['?'] * len(weekday_range))})
              AND date(?) BETWEEN date(lessons.start_date) AND date(lessons.end_date)
            ORDER BY lessons.weekday, lessons.pair_number
        """, (group_id, *weekday_range, today_str))

    lessons = cursor.fetchall()
    conn.close()

    if not lessons:
        return "📝 Расписание не найдено."

    days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    msg = ""
    last_day = -1
    for lesson in lessons:
        day = lesson['weekday']
        if mode == 'week' and day != last_day:
            msg += f"\n📅 <b>{days[day]}</b>\n"
            last_day = day
        msg += f"⏰ {lesson['start_time']}–{lesson['end_time']}: <b>{lesson['subject_name']}</b>\n"
        msg += f"   📍 Ауд. {lesson['room_number']} ({lesson['building']})\n"
    return msg

# Заглушка "Мероприятия"
@bot.message_handler(func=lambda m: m.text == "📋 Мероприятия")
def handle_events(message):
    bot.send_message(message.chat.id, "🛠 Раздел мероприятий в разработке!")

# Переключение "Тихого режима"
@bot.message_handler(func=lambda m: m.text in ["🔕 Включить", "🔔 Выключить"])
def toggle_silent_mode(message):
    chat_id = message.chat.id
    conn = getDBConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT silent_mode FROM users WHERE telegram_id = ?", (chat_id,))
    user = cursor.fetchone()

    if user:
        new_mode = 0 if user["silent_mode"] else 1
        cursor.execute("UPDATE users SET silent_mode = ? WHERE telegram_id = ?", (new_mode, chat_id))
        conn.commit()

    conn.close()
    send_main_menu(chat_id)

bot.infinity_polling()
