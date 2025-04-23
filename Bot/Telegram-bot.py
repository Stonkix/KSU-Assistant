import telebot
import sqlite3
import os
import threading
import time
from telebot import types
from datetime import datetime, timedelta, date
from Utils.Utils import verifyPassword

dbDir = "C:/Users/alexa/Desktop/KSU-Assistant-after-venv/Utils"
DATABASE_PATH = os.path.join(dbDir, "university.db")
botToken = '7637461107:AAFH6C5oy9WZIuQhZfkmH6YUbVNseduRA90'
bot = telebot.TeleBot(botToken)
user_states = {}

# Глобальные переменные для управления потоками уведомлений
notification_thread = None
stop_notifications = False

def adapt_date_iso(val):
    return val.isoformat()

sqlite3.register_adapter(date, adapt_date_iso)

def getDBConnection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

WEEKDAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
WEEKDAYS_RU = {
    1: 'Понедельник',
    2: 'Вторник',
    3: 'Среда',
    4: 'Четверг',
    5: 'Пятница',
    6: 'Суббота',
    7: 'Воскресенье'
}
notified_lessons = set()
def check_schedule_changes():
    """
    Функция для проверки изменений в расписании и отправки уведомлений
    """
    conn = getDBConnection()
    cursor = conn.cursor()

    # Получаем текущее расписание (кешируем)
    cursor.execute("""
        SELECT l.id, l.group_id, l.teacher_id, l.weekday, l.pair_number, 
               s.name as subject_name, r.room_number, r.building,
               pt.start_time, pt.end_time
        FROM lessons l
        JOIN subjects s ON l.subject_id = s.id
        JOIN rooms r ON l.room_id = r.id
        JOIN pair_times pt ON l.pair_number = pt.pair_number
    """)
    current_schedule = {row['id']: dict(row) for row in cursor.fetchall()}

    try:
        while not stop_notifications:
            time.sleep(2)

            # Получаем новое состояние расписания
            cursor.execute("""
                SELECT l.id, l.group_id, l.teacher_id, l.weekday, l.pair_number, 
                       s.name as subject_name, r.room_number, r.building,
                       pt.start_time, pt.end_time
                FROM lessons l
                JOIN pair_times pt ON l.pair_number = pt.pair_number
                JOIN subjects s ON l.subject_id = s.id
                JOIN rooms r ON l.room_id = r.id
                WHERE date('now') BETWEEN date(l.start_date) AND date(l.end_date)
            """)
            new_schedule = {row['id']: dict(row) for row in cursor.fetchall()}

            # Проверяем изменения
            changed_lessons = []

            # 1. Удаленные
            for lesson_id in set(current_schedule.keys()) - set(new_schedule.keys()):
                changed_lessons.append(('deleted', current_schedule[lesson_id]))

            # 2. Добавленные
            for lesson_id in set(new_schedule.keys()) - set(current_schedule.keys()):
                changed_lessons.append(('added', new_schedule[lesson_id]))

            # 3. Измененные
            for lesson_id in set(current_schedule.keys()) & set(new_schedule.keys()):
                old_lesson = current_schedule[lesson_id]
                new_lesson = new_schedule[lesson_id]

                changes = []
                if old_lesson['subject_name'] != new_lesson['subject_name']:
                    changes.append(('subject', old_lesson['subject_name'], new_lesson['subject_name']))
                if old_lesson['room_number'] != new_lesson['room_number'] or old_lesson['building'] != new_lesson['building']:
                    changes.append(('room', f"{old_lesson['room_number']} ({old_lesson['building']})", f"{new_lesson['room_number']} ({new_lesson['building']})"))
                if old_lesson['weekday'] != new_lesson['weekday']:
                    changes.append(('weekday', old_lesson['weekday'], new_lesson['weekday']))
                if old_lesson['pair_number'] != new_lesson['pair_number']:
                    changes.append(('time', f"{old_lesson['start_time']}-{old_lesson['end_time']}", f"{new_lesson['start_time']}-{new_lesson['end_time']}"))

                if changes:
                    changed_lessons.append(('modified', {
                        'id': lesson_id,
                        'changes': changes,
                        'group_id': new_lesson['group_id'],
                        'teacher_id': new_lesson['teacher_id'],
                        'weekday': new_lesson['weekday'],
                        'pair_number': new_lesson['pair_number']
                    }))

            # Обработка изменений
            for change_type, lesson_data in changed_lessons:
                message = ""

                # Проверяем, отправляли ли уже уведомление для этого урока
                if lesson_data['id'] in notified_lessons:
                    continue  # Если уведомление уже отправлялось, пропускаем

                # Запрашиваем название группы из таблицы academic_groups
                cursor.execute("SELECT name FROM academic_groups WHERE id = ?", (lesson_data['group_id'],))
                group_name_row = cursor.fetchone()
                group_name = group_name_row['name'] if group_name_row else f"Группа {lesson_data['group_id']}"

                if change_type == 'modified':
                    change_descriptions = []
                    for field, old_val, new_val in lesson_data['changes']:
                        if field == 'subject':
                            change_descriptions.append(f"📚 Предмет: \"{old_val}\" → \"{new_val}\"")
                        elif field == 'room':
                            change_descriptions.append(f"🏫 Аудитория: \"{old_val}\" → \"{new_val}\"")
                        elif field == 'weekday':
                            old_weekday_name = WEEKDAYS_RU.get(int(old_val) - 1, old_val)
                            new_weekday_name = WEEKDAYS_RU.get(int(new_val) - 1, new_val)
                            change_descriptions.append(f"📅 День недели: \"{old_weekday_name}\" → \"{new_weekday_name}\"")
                        elif field == 'time':
                            change_descriptions.append(f"⏰ Время: \"{old_val}\" → \"{new_val}\"")

                    if change_descriptions:
                        message = (
                            f"✏ Изменения в паре:\n"
                            f"📍 Пара #{lesson_data['pair_number']} для группы {group_name}:\n"
                            + "\n".join(change_descriptions)
                        )

                if message:
                    try:
                        # Отправляем уведомление студентам
                        cursor.execute(
                            "SELECT u.telegram_id FROM users u JOIN students s ON u.id = s.user_id WHERE s.group_id = ? AND (u.silent_mode IS NULL OR u.silent_mode != 1)",
                            (lesson_data['group_id'],))
                        for row in cursor.fetchall():
                            try:
                                bot.send_message(row['telegram_id'], message)
                            except Exception as e:
                                print(f"Failed to send notification to {row['telegram_id']}: {e}")

                        # Отправляем уведомление преподавателю
                        cursor.execute(
                            "SELECT u.telegram_id FROM users u WHERE u.id = ? AND (u.silent_mode IS NULL OR u.silent_mode != 1)",
                            (lesson_data['teacher_id'],))
                        for row in cursor.fetchall():
                            try:
                                bot.send_message(row['telegram_id'], message)
                            except Exception as e:
                                print(f"Failed to send notification to {row['telegram_id']}: {e}")

                        # Добавляем ID урока в множество, чтобы больше не отправлять уведомление для этого урока
                        notified_lessons.add(lesson_data['id'])

                    except Exception as e:
                        print(f"Error sending notification: {e}")
    except Exception as e:
        print(f"Error in checking schedule changes: {e}")
    finally:
        conn.close()


def start_notifications():
    """
    Запускает потоки для проверки изменений в расписании и предстоящих пар
    """
    global notification_threads, stop_notifications
    stop_notifications = False

    # Создаем список для хранения потоков
    notification_threads = []

    # Создаем и запускаем поток для проверки изменений расписания
    schedule_thread = threading.Thread(target=check_schedule_changes)
    schedule_thread.start()
    notification_threads.append(schedule_thread)

    # Создаем и запускаем поток для проверки предстоящих пар
    # upcoming_thread = threading.Thread(target=check_upcoming_lessons)
   # upcoming_thread.start()
    #notification_threads.append(upcoming_thread)


def stop_notifications():
    """
    Останавливает все потоки уведомлений
    """
    global stop_notifications
    stop_notifications = True

    # Дожидаемся завершения всех потоков
    if 'notification_threads' in globals():
        for thread in notification_threads:
            if thread.is_alive():
                thread.join()


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
    week_btn = types.KeyboardButton("📅 Числитель/Знаменатель?")
    silent_btn = types.KeyboardButton(silent_text)
    markup.add(schedule_btn, events_btn, silent_btn, week_btn)
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
    # FIXED: Добавляем +1 для соответствия формату базы данных (1-7)
    weekday = today.weekday() + 1
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
    msg = ""
    last_day = -1
    for lesson in lessons:
        day = lesson['weekday']
        if mode == 'week' and day != last_day:
            msg += f"\n📅 <b>{WEEKDAYS[day - 1]}</b>\n"  # -1 потому что в базе 1-7
            last_day = day
        msg += f"⏰ {lesson['start_time']}–{lesson['end_time']}: <b>{lesson['subject_name']}</b>\n"
        msg += f"   👨‍🏫 {lesson['teacher_name']}\n"
        msg += f"   📍 Ауд. {lesson['room_number']} ({lesson['building']})\n"
    return msg


def fetch_teacher_schedule(user_id, mode='today'):
    conn = getDBConnection()
    cursor = conn.cursor()

    today = datetime.today()
    weekday = today.weekday() + 1
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
    msg = ""
    last_day = -1
    for lesson in lessons:
        day = lesson['weekday']
        if mode == 'week' and day != last_day:
            msg += f"\n📅 <b>{WEEKDAYS[day - 1]}</b>\n"  # -1 потому что в базе 1-7
            last_day = day
        msg += f"⏰ {lesson['start_time']}–{lesson['end_time']}: <b>{lesson['subject_name']}</b>\n"
        msg += f"   👥 Группа: {lesson['group_name']}\n"
        msg += f"   📍 Ауд. {lesson['room_number']} ({lesson['building']})\n"
    return msg


# Обработчик кнопки "📋 Мероприятия"
@bot.message_handler(func=lambda m: m.text == "📋 Мероприятия")
def handle_events(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    new_events_btn = types.KeyboardButton("❓ Узнать о новых мероприятиях")
    history_btn = types.KeyboardButton("🗂 История посещенных мероприятий")
    back_btn = types.KeyboardButton("⬅️ Назад в меню")
    markup.add(new_events_btn, history_btn, back_btn)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


# Обработчик подменю мероприятий
@bot.message_handler(
    func=lambda m: m.text in ["❓ Узнать о новых мероприятиях", "🗂 История посещенных мероприятий", "⬅️ Назад в меню"])
def handle_events_submenu(message):
    chat_id = message.chat.id

    if message.text == "⬅️ Назад в меню":
        send_main_menu(chat_id)
        return

    conn = getDBConnection()
    cursor = conn.cursor()

    try:
        # Получаем информацию о пользователе
        cursor.execute("SELECT id, role FROM users WHERE telegram_id = ?", (chat_id,))
        user = cursor.fetchone()
        if not user:
            bot.send_message(chat_id, "❌ Вы не авторизованы.")
            return

        user_id = user["id"]
        user_role = user["role"]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if message.text == "❓ Узнать о новых мероприятиях":
            # Показываем будущие мероприятия, на которые можно записаться
            cursor.execute("""
                SELECT e.id, e.title, e.datetime, e.description, e.target_roles,
                       CASE WHEN ep.user_id IS NOT NULL THEN 1 ELSE 0 END as is_registered
                FROM events e
                LEFT JOIN event_participants ep ON e.id = ep.event_id AND ep.user_id = ?
                WHERE (e.target_roles IN ('both', ?)) 
                  AND e.datetime > ?
                ORDER BY e.datetime ASC
            """, (user_id, user_role, now))

            events = cursor.fetchall()

            if not events:
                bot.send_message(chat_id, "На данный момент нет доступных мероприятий.")
                return

            for event in events:
                markup = types.InlineKeyboardMarkup()

                if event['is_registered']:
                    cancel_button = types.InlineKeyboardButton("❌ Отменить запись",
                                                               callback_data=f"leave_{event['id']}")
                    markup.add(cancel_button)
                    status_text = "✅ Вы записаны"
                else:
                    join_button = types.InlineKeyboardButton("🔗 Записаться", callback_data=f"join_{event['id']}")
                    markup.add(join_button)
                    status_text = ""

                event_text = f"🎉 <b>{event['title']}</b>\n"
                event_text += f"📅 Дата: {event['datetime']}\n"
                event_text += f"📍 {event['description']}\n"
                if status_text:
                    event_text += f"\n{status_text}\n"

                bot.send_message(
                    chat_id,
                    event_text,
                    parse_mode="HTML",
                    reply_markup=markup
                )

        elif message.text == "🗂 История посещенных мероприятий":
            # Показываем мероприятия, на которые пользователь записывался
            cursor.execute("""
                SELECT e.id, e.title, e.datetime, e.description,
                       CASE WHEN e.datetime < ? THEN 1 ELSE 0 END as is_past
                FROM events e
                JOIN event_participants ep ON e.id = ep.event_id
                WHERE ep.user_id = ?
                ORDER BY e.datetime DESC
            """, (now, user_id))

            events = cursor.fetchall()

            if not events:
                bot.send_message(chat_id, "Вы еще не записывались ни на одно мероприятие.")
                return

            for event in events:
                event_text = f"🎫 <b>{event['title']}</b>\n"
                event_text += f"📅 Дата: {event['datetime']}\n"
                event_text += f"📍 {event['description']}\n"

                if event['is_past']:
                    event_text += "\n🔹 Мероприятие уже прошло\n"
                else:
                    markup = types.InlineKeyboardMarkup()
                    cancel_button = types.InlineKeyboardButton("❌ Отменить запись",
                                                               callback_data=f"leave_{event['id']}")
                    markup.add(cancel_button)
                    event_text += "\n🔹 Вы записаны\n"
                    bot.send_message(
                        chat_id,
                        event_text,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                    continue

                bot.send_message(
                    chat_id,
                    event_text,
                    parse_mode="HTML"
                )

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка при получении мероприятий: {str(e)}")
    finally:
        conn.close()


@bot.message_handler(func=lambda m: m.text == "📅 Числитель/Знаменатель?")
def week(message):
    numberWeek = datetime.now().isocalendar().week
    if (numberWeek % 2 == 0):
        bot.send_message(message.chat.id, "📆 Сейчас числитель.", parse_mode="HTML", )
    else:
        bot.send_message(message.chat.id, "📆 Сейчас знаминатель.", parse_mode="HTML", )


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

        # Получаем внутренний ID пользователя
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (chat_id,))
        user = cursor.fetchone()
        if not user:
            bot.answer_callback_query(call.id, "Ошибка: пользователь не найден.")
            return
        user_id = user["id"]

        # Проверяем, не записан ли уже пользователь
        cursor.execute("SELECT * FROM event_participants WHERE event_id = ? AND user_id = ?", (event_id, user_id))
        if cursor.fetchone():
            bot.answer_callback_query(call.id, "Вы уже записаны на это мероприятие!")
            return

        # Записываем пользователя
        cursor.execute("INSERT INTO event_participants (event_id, user_id, status) VALUES (?, ?, 'going')",
                       (event_id, user_id))
        conn.commit()

        bot.clear_step_handler_by_chat_id(chat_id)
        bot.delete_message(chat_id, message_id)

        bot.send_message(chat_id, f"✅ Вы успешно записаны на мероприятие: {event['title']}!")
        handle_events_submenu(call.message)

    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")
    finally:
        conn.close()



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

        # Получаем внутренний ID пользователя
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (chat_id,))
        user = cursor.fetchone()
        if not user:
            bot.answer_callback_query(call.id, "Ошибка: пользователь не найден.")
            return
        user_id = user["id"]

        # Проверяем, записан ли пользователь
        cursor.execute("SELECT * FROM event_participants WHERE event_id = ? AND user_id = ?", (event_id, user_id))
        if not cursor.fetchone():
            bot.answer_callback_query(call.id, "Вы не записаны на это мероприятие!")
            return

        # Удаляем запись
        cursor.execute("DELETE FROM event_participants WHERE event_id = ? AND user_id = ?", (event_id, user_id))
        conn.commit()

        bot.clear_step_handler_by_chat_id(chat_id)
        bot.delete_message(chat_id, message_id)

        bot.send_message(chat_id, f"❌ Вы отменили запись на мероприятие: {event['title']}!")
        handle_events_submenu(call.message)

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


# Запуск проверки изменений в расписании
start_notifications()
bot.infinity_polling()
# При завершении работы бота
stop_notifications()