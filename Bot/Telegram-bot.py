import telebot
import sqlite3
import os

from telebot import types
from Utils.Utils import hashPassword, verifyPassword

dbDir = "C:/Users/alexa/Desktop/KSU-Assistant/Utils" #Путь к директории с базой данных
DATABASE_PATH = os.path.join(dbDir, "university.db")
botToken = '7637461107:AAFH6C5oy9WZIuQhZfkmH6YUbVNseduRA90'
DATABASE_NAME = 'university.db'

bot = telebot.TeleBot(botToken) # Наш бот находится по тегу @tksu_bot
user_states = {} # Словарь для хранения временных данных пользователей во время авторизации

def getDBConnection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@bot.message_handler(commands = ['start', 'login'])
def handleStart(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    bot.send_message(chat_id, 'Для входа введите корпоративную почту (например, @studklg.ru или @tksu.ru):')
    user_states[chat_id] = {'state': 'WAIT_EMAIL'}

# Обработка ввода почты
@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('state') == 'WAIT_EMAIL')
def handle_email(message):
    chat_id = message.chat.id
    email = message.text.strip()
    # Проверяем домен
    if not (email.endswith('@studklg.ru') or email.endswith('@tksu.ru')):
        bot.send_message(chat_id, 'Неподдерживаемый домен почты. Используйте @studklg.ru или @tksu.ru.')
        return

    conn = getDBConnection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        bot.send_message(chat_id, 'Пользователь с такой почтой не найден. Обратитесь к администратору.')
        return

# Проверяем, не привязан ли уже
    if user['telegram_id'] is not None:
        if str(user['telegram_id']) == str(chat_id):
            bot.send_message(chat_id, 'Вы уже авторизованы.')
        else:
            bot.send_message(chat_id, 'Этот email уже привязан к другому аккаунту Telegram.')
        user_states.pop(chat_id, None)
        return

    # Все ок, просим пароль
    user_states[chat_id] = {'state': 'WAIT_PASSWORD', 'email': email}
    bot.send_message(chat_id, 'Введите пароль:')

# Обработка ввода пароля
@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('state') == 'WAIT_PASSWORD')
def handle_password(message):
    chat_id = message.chat.id
    password = message.text.strip()
    email = user_states[chat_id]['email']

    conn = getDBConnection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()

    if not verifyPassword(user['password_hash'], password):
        bot.send_message(chat_id, 'Неверный пароль. Попробуйте еще раз.')
        conn.close()
        return

    # Обновляем telegram_id
    cursor.execute('UPDATE users SET telegram_id = ? WHERE email = ?', (chat_id, email))
    conn.commit()
    conn.close()

    role = user['role']
    bot.send_message(chat_id, f'Успешно авторизованы как {role}.')
    user_states.pop(chat_id, None)



bot.infinity_polling()


