from django.shortcuts import render, redirect
from django.http import HttpResponse
from django import forms
from django.db import connection
from django.utils.safestring import mark_safe
from urllib.parse import urlencode

import sys
from pathlib import Path
from collections import defaultdict

sys.path.append(str(Path(__file__).resolve().parents[3] / 'Utils'))

import Utils

import socket
import threading

IP = "127.0.0.1"
PORT = 1922


# IP = input("Я захотел ввести IP второй раз: ")

def send(message):
    with socket.socket() as conn:
        conn.connect((IP, PORT))
        print("Соединение")
        conn.send(message.encode())

def generate_message_form():
    form = '''
            <!-- Поле для текстового сообщения -->
            <p>
                <label for="message">Сообщение:</label>
                <input type="text" name="message" id="message"></input>
            </p>

            <!-- Чекбоксы для выбора аудитории -->
            <p>
                <input type="checkbox" name="for_teachers" id="for_teachers" value="0">
                <label for="for_teachers">Для преподавателей</label>

                <input type="checkbox" name="for_students" id="for_students" value="1">
                <label for="for_students">Для студентов</label>
            </p>
    '''
    return form


def broadcastPage(request):
    form = generate_message_form()

    if request.method == "POST":
        keys = []
        values = []
        for key, value in request.POST.items():
            if key == 'csrfmiddlewaretoken':
                continue

            # if key == '':
            if value == '':
                values.append('NULL')
            else:
                values.append(f"\'{value}\'")

            keys.append(key)
        print(f'keys {keys}, values {values}')
        message = values[0] + '~/'
        for key in keys:
            if key == 'message':
                continue
            else:
                message += key
                message += '&'

        print(f'messege {message}')
        send(message)

    renderPage = render(request, 'main/broadcast.html',
                        {'form': mark_safe(form)})

    return renderPage