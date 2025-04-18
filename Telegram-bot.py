import telebot
bot = telebot.TeleBot("7637461107:AAFH6C5oy9WZIuQhZfkmH6YUbVNseduRA90") #Наш бот находится по тегу @tksu_bot

@bot.message_handler(commands = ['start'])
def say_hello(message):
    bot.send_message(message.chat.id, 'Привет, я твой ассистент')

bot.polling(none_stop = 'true')


