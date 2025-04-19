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

@bot.message_handler(commands = ['start'])
def say_hello(message):
    bot.send_message(message.chat.id, 'Привет, я твой ассистент')

def getDBConnection():
    connect = sqlite3.connect(DATABASE_PATH)
    connect.row_factory = sqlite3.Row
    return connect


bot.infinity_polling()


