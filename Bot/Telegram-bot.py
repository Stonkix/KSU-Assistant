import telebot
import sqlite3
import os
from telebot import types
from datetime import datetime, timedelta
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
    schedule_btn = types.KeyboardButton("📅 Расписание")
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


# Обработчик расписания
@bot.message_handler(func=lambda m: m.text in ["📅 Расписание", "📆 Сегодня", "🗓️ На неделю", "⬅️ Назад"])
def handle_schedule(message):
    chat_id = message.chat.id

    if message.text == "📅 Расписание":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        today_btn = types.KeyboardButton("📆 Сегодня")
        week_btn = types.KeyboardButton("🗓️ На неделю")
        back_btn = types.KeyboardButton("⬅️ Назад")
        markup.add(today_btn, week_btn, back_btn)
        bot.send_message(chat_id, "Выберите период:", reply_markup=markup)
        return

    if message.text == "⬅️ Назад":
        send_main_menu(chat_id)
        return

    mode = 'today' if message.text == "📆 Сегодня" else 'week'

    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, role FROM users WHERE telegram_id = ?", (chat_id,))
        user = cursor.fetchone()

        if not user:
            bot.send_message(chat_id, "❌ Вы не авторизованы.")
            return

        user_id = user["id"]
        user_role = user["role"]

        if user_role == 'student':
            schedule_text = fetch_student_schedule(user_id, mode)
        elif user_role == 'teacher':
            schedule_text = fetch_teacher_schedule(user_id, mode)
        else:
            schedule_text = "❌ Ваша роль не поддерживает просмотр расписания."

        bot.send_message(chat_id, schedule_text, parse_mode="HTML")

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка при получении расписания: {str(e)}")
    finally:
        conn.close()


def fetch_student_schedule(user_id, mode='today'):
    conn = getDBConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT group_id FROM students WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "❌ Вы не назначены в группу."

    group_id = row["group_id"]
    today = datetime.today()
    weekday = today.weekday()
    today_str = today.strftime('%Y-%m-%d')

    if mode == 'today':
        cursor.execute(""" 
            SELECT lessons.weekday, lessons.pair_number, pair_times.start_time, pair_times.end_time,
                   subjects.name AS subject_name, rooms.room_number, rooms.building,
                   teachers.full_name AS teacher_name
            FROM lessons
            JOIN pair_times ON lessons.pair_number = pair_times.pair_number
            JOIN subjects ON lessons.subject_id = subjects.id
            JOIN rooms ON lessons.room_id = rooms.id
            JOIN teachers ON lessons.teacher_id = teachers.user_id
            WHERE lessons.group_id = ? AND lessons.weekday = ?
              AND date(?) BETWEEN date(lessons.start_date) AND date(lessons.end_date)
            ORDER BY lessons.pair_number
        """, (group_id, weekday, today_str))
    else:
        week_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        weekday_range = tuple(i for i in range(7))
        cursor.execute(f"""
            SELECT lessons.weekday, lessons.pair_number, pair_times.start_time, pair_times.end_time,
                   subjects.name AS subject_name, rooms.room_number, rooms.building,
                   teachers.full_name AS teacher_name
            FROM lessons
            JOIN pair_times ON lessons.pair_number = pair_times.pair_number
            JOIN subjects ON lessons.subject_id = subjects.id
            JOIN rooms ON lessons.room_id = rooms.id
            JOIN teachers ON lessons.teacher_id = teachers.user_id
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
        msg += f"   👨‍🏫 {lesson['teacher_name']}\n"
        msg += f"   📍 Ауд. {lesson['room_number']} ({lesson['building']})\n"
    return msg


def fetch_teacher_schedule(user_id, mode='today'):
    conn = getDBConnection()
    cursor = conn.cursor()

    today = datetime.today()
    weekday = today.weekday()
    today_str = today.strftime('%Y-%m-%d')

    if mode == 'today':
        cursor.execute(""" 
            SELECT lessons.weekday, lessons.pair_number, pair_times.start_time, pair_times.end_time,
                   subjects.name AS subject_name, rooms.room_number, rooms.building,
                   academic_groups.name AS group_name
            FROM lessons
            JOIN pair_times ON lessons.pair_number = pair_times.pair_number
            JOIN subjects ON lessons.subject_id = subjects.id
            JOIN rooms ON lessons.room_id = rooms.id
            JOIN academic_groups ON lessons.group_id = academic_groups.id
            WHERE lessons.teacher_id = ? AND lessons.weekday = ?
              AND date(?) BETWEEN date(lessons.start_date) AND date(lessons.end_date)
            ORDER BY lessons.pair_number
        """, (user_id, weekday, today_str))
    else:
        week_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        weekday_range = tuple(i for i in range(7))
        cursor.execute(f"""
            SELECT lessons.weekday, lessons.pair_number, pair_times.start_time, pair_times.end_time,
                   subjects.name AS subject_name, rooms.room_number, rooms.building,
                   academic_groups.name AS group_name
            FROM lessons
            JOIN pair_times ON lessons.pair_number = pair_times.pair_number
            JOIN subjects ON lessons.subject_id = subjects.id
            JOIN rooms ON lessons.room_id = rooms.id
            JOIN academic_groups ON lessons.group_id = academic_groups.id
            WHERE lessons.teacher_id = ?
              AND lessons.weekday IN ({','.join(['?'] * len(weekday_range))})
              AND date(?) BETWEEN date(lessons.start_date) AND date(lessons.end_date)
            ORDER BY lessons.weekday, lessons.pair_number
        """, (user_id, *weekday_range, today_str))

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
        msg += f"   👥 Группа: {lesson['group_name']}\n"
        msg += f"   📍 Ауд. {lesson['room_number']} ({lesson['building']})\n"
    return msg


# Обработчик кнопки "📋 Мероприятия"
@bot.message_handler(func=lambda m: m.text == "📋 Мероприятия")
def handle_events(message):
    conn = getDBConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE telegram_id = ?", (message.chat.id,))
    user = cursor.fetchone()
    if not user:
        bot.send_message(message.chat.id, "❌ Вы не авторизованы.")
        return

    user_role = user['role']

    cursor.execute("""
        SELECT events.id, events.title, events.datetime, events.description, events.target_roles
        FROM events
        WHERE events.target_roles IN ('both', ?) OR (events.target_roles = 'both' AND events.group_id IS NULL)
        ORDER BY events.datetime ASC
    """, (user_role,))

    events = cursor.fetchall()
    conn.close()

    if not events:
        bot.send_message(message.chat.id, "На данный момент нет доступных мероприятий.")
        return

    for event in events:
        markup = types.InlineKeyboardMarkup()
        conn = getDBConnection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM event_participants WHERE event_id = ? AND user_id = ?",
                       (event['id'], message.chat.id))
        existing_registration = cursor.fetchone()

        if existing_registration:
            cancel_button = types.InlineKeyboardButton("❌ Отменить запись", callback_data=f"leave_{event['id']}")
            markup.add(cancel_button)
        else:
            join_button = types.InlineKeyboardButton("🔗 Записаться", callback_data=f"join_{event['id']}")
            markup.add(join_button)

        event_text = f"🎉 <b>{event['title']}</b>\n"
        event_text += f"📅 Дата: {event['datetime']}\n"
        event_text += f"📍 {event['description']}\n"

        bot.send_message(
            message.chat.id,
            event_text,
            parse_mode="HTML",
            reply_markup=markup
        )


# Обработчик записи на мероприятие
@bot.callback_query_handler(func=lambda call: call.data.startswith('join_'))
def join_event(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    event_id = int(call.data.split('_')[1])

    try:
        conn = getDBConnection()
        cursor = conn.cursor()

        # Проверяем существование мероприятия
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        event = cursor.fetchone()

        if not event:
            bot.answer_callback_query(call.id, "Это мероприятие не существует.")
            return

        # Проверяем, не записан ли уже пользователь
        cursor.execute("SELECT * FROM event_participants WHERE event_id = ? AND user_id = ?",
                       (event_id, chat_id))
        if cursor.fetchone():
            bot.answer_callback_query(call.id, "Вы уже записаны на это мероприятие!")
            return

        # Записываем пользователя
        cursor.execute("INSERT INTO event_participants (event_id, user_id, status) VALUES (?, ?, 'going')",
                       (event_id, chat_id))
        conn.commit()

        # Удаляем все предыдущие сообщения с мероприятиями
        bot.clear_step_handler_by_chat_id(chat_id)
        bot.delete_message(chat_id, message_id)

        # Отправляем подтверждение
        bot.send_message(chat_id, f"✅ Вы успешно записаны на мероприятие: {event['title']}!")

        # Обновляем список мероприятий
        handle_events(call.message)

    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")
    finally:
        conn.close()


# Обработчик отмены записи
@bot.callback_query_handler(func=lambda call: call.data.startswith('leave_'))
def leave_event(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    event_id = int(call.data.split('_')[1])

    try:
        conn = getDBConnection()
        cursor = conn.cursor()

        # Проверяем существование мероприятия
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        event = cursor.fetchone()

        if not event:
            bot.answer_callback_query(call.id, "Это мероприятие не существует.")
            return

        # Проверяем, записан ли пользователь
        cursor.execute("SELECT * FROM event_participants WHERE event_id = ? AND user_id = ?",
                       (event_id, chat_id))
        if not cursor.fetchone():
            bot.answer_callback_query(call.id, "Вы не записаны на это мероприятие!")
            return

        # Удаляем запись
        cursor.execute("DELETE FROM event_participants WHERE event_id = ? AND user_id = ?",
                       (event_id, chat_id))
        conn.commit()

        # Удаляем все предыдущие сообщения с мероприятиями
        bot.clear_step_handler_by_chat_id(chat_id)
        bot.delete_message(chat_id, message_id)

        # Отправляем подтверждение
        bot.send_message(chat_id, f"❌ Вы отменили запись на мероприятие: {event['title']}!")

        # Обновляем список мероприятий
        handle_events(call.message)

    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")
    finally:
        conn.close()


# Обработчик кнопки "Включить/Выключить тихий режим"
@bot.message_handler(func=lambda m: m.text == "🔕 Включить" or m.text == "🔔 Выключить")
def toggle_silent_mode(message):
    chat_id = message.chat.id
    conn = getDBConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT silent_mode FROM users WHERE telegram_id = ?", (chat_id,))
    user = cursor.fetchone()

    if user:
        new_silent_mode = 0 if user['silent_mode'] else 1
        cursor.execute("UPDATE users SET silent_mode = ? WHERE telegram_id = ?", (new_silent_mode, chat_id))
        conn.commit()
        conn.close()

        new_silent_text = "🔕 Включить" if new_silent_mode == 0 else "🔔 Выключить"
        send_main_menu(chat_id)
        bot.send_message(chat_id, f"🔊 Тихий режим {'выключен' if new_silent_mode == 0 else 'включен'}.")
    else:
        bot.send_message(chat_id, "❌ Вы не авторизованы.")
        conn.close()


bot.infinity_polling()
