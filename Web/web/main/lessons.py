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


def GETGroup(request):
    group = request.GET.get('groupId')
    if group is not None:
        print(f'groupId: {group}')
        return group
    return None


def GETId(request):
    id = request.GET.get('id')
    if id is not None:
        print(f'id: {id}')
        return id
    return None


def GETWeekDay(request):
    weekDay = request.GET.get('weekday')
    if weekDay is not None:
        print(f'weekDay: {weekDay}')
        return weekDay
    return None


def GETPairNumber(request):
    pairNumber = request.GET.get('pair-number')
    if pairNumber is not None:
        print(f'pairNumber: {pairNumber}')
        return pairNumber
    return None


def generateGroupList():
    groupList = ''
    with connection.cursor() as cursor:
        query = f"""
        SELECT *
        FROM academic_groups
        """
        cursor.execute(query)
        groups = cursor.fetchall()

    for group_id, group_name in groups:
        string = f'<li><a href="?groupId={group_id}"><button>{group_name}</button></a></li>'
        groupList += string
    return groupList


def generateHTMLTimeTable(group):
    dictWeekDays = {
        1: 'Понедельник',
        2: 'Вторник',
        3: 'Среда',
        4: 'Четверг',
        5: 'Пятница',
        6: 'Суббота',
        7: 'Воскресение',
    }

    dictWeekParity = {
        'even': 'Числитель',
        'odd': 'Знаменатель',
    }

    with connection.cursor() as cursor:
        query = f'SELECT id, name FROM subjects'
        cursor.execute(query)
        subjects = cursor.fetchall()
        dictSubjects = {}
        for column in subjects:
            dictSubjects[column[0]] = column[1]

    with connection.cursor() as cursor:
        query = f'SELECT * FROM rooms'
        cursor.execute(query)
        rooms = cursor.fetchall()
        dictRooms = {}
        for column in rooms:
            dictRooms[column[0]] = (column[1], column[2]) # (room_number, building)

    with connection.cursor() as cursor:
        query = f'SELECT user_id, full_name FROM teachers'
        cursor.execute(query)
        teachers = cursor.fetchall()
        dictTeachers = {}
        for column in teachers:
            dictTeachers[column[0]] = column[1]

    with connection.cursor() as cursor:
        query = f'SELECT * FROM lessons WHERE group_id = {group}'
        print(query)
        cursor.execute(query)
        lessons = cursor.fetchall()
        print(lessons)

    dictLessons = defaultdict(list)
    for row in lessons:
        day = row[7] # weekday
        pair = row[8] # pair_number
        dictLessons[(day, pair)].append(row)

    with connection.cursor() as cursor:
        query = f'SELECT * FROM pair_times'
        print(query)
        cursor.execute(query)
        pairTimes = cursor.fetchall()

    table = ''

    table += '<tr class="noHover">'
    table += '<td>Время</td>'
    for weekDay in dictWeekDays:
        table += f'<td>{dictWeekDays[weekDay]}</td>'
    table += '</tr>'

    for pair_number, start_time, end_time in pairTimes:
        table += '<tr class="noHover">'
        table += f'<td>{start_time}-{end_time}</td>'
        for weekDay in dictWeekDays:
            if (weekDay, pair_number) in dictLessons:
                table += '<td>'
                for lesson in dictLessons.get((weekDay, pair_number), []):

                    table += f"""<div class="filled-cell" id="{lesson[0]}">
                                    {dictSubjects[lesson[1]]}<br>
                                    {dictTeachers[lesson[2]]}<br>
                                    {dictRooms[lesson[4]][0]} к.{dictRooms[lesson[4]][1]}<br>
                                    {lesson[5]} по {lesson[6]}<br>
                                    {dictWeekParity[lesson[-1]]}<br>
                                </div>"""
                table += f'<div class="empty-cell" weekday="{weekDay}" pair-number="{pair_number}">+</div>'
                table += '</td>'
            else:
                table += '<td>'
                table += f'<div class="empty-cell" weekday="{weekDay}" pair-number="{pair_number}">+</div>'
                table += '</td>'
        table += '</tr>'


    return table


def generateFormForNewLesson(group, weekDay, pairNumber):
    dictColumns = {
        'subject_id' : 'Предмет',
        'teacher_id' : 'Преподаватель',
        'room_id' : 'Кабинет',
        'start_date' : 'Начало (ГГГГ-ММ-ДД)',
        'end_date' : 'Конец (ГГГГ-ММ-ДД)',
        'week_parity' : 'Числитель/Знаменатель'
    }

    with connection.cursor() as cursor:
        query = f"""
        SELECT *
        FROM subjects
        """
        cursor.execute(query)
        subjects = cursor.fetchall()

    with connection.cursor() as cursor:
        query = f"""
        SELECT *
        FROM teachers
        """
        cursor.execute(query)
        teachers = cursor.fetchall()

    with connection.cursor() as cursor:
        query = f"""
        SELECT *
        FROM rooms
        """
        cursor.execute(query)
        rooms = cursor.fetchall()

    form = ''

    form += '<p><label for="subject_id">Предмет</label>'
    form += '<select name="subject_id">'
    form += '<option value="" selected disabled>Выберите предмет</option>'
    for subject in subjects: # id, name
        form += f'<option value="{subject[0]}">{subject[1]}</option>'
    form += '</select></p>'

    form += '<p><label for="teacher_id">Преподаватель</label>'
    form += '<select name="teacher_id">'
    form += '<option value="" selected disabled>Выберите преподавателя</option>'
    for teacher in teachers:  # user_id, full_name
        form += f'<option value="{teacher[0]}">{teacher[1]}</option>'
    form += '</select></p>'

    form += f'<input type=\"hidden\" name=\"group_id\" value=\"{group}\">'

    form += '<p><label for="room_id">Кабинет</label>'
    form += '<select name="room_id">'
    form += '<option value="" selected disabled>Выберите кабинет</option>'
    for room in rooms:  # id, room_number, building
        form += f'<option value="{room[0]}">{room[1]} к.{room[2]}</option>'
    form += '</select></p>'

    form += f'''
                <p><label for=\"start_date\">Начало (ГГГГ-ММ-ДД)</label>
                <input type=\"text\" name=\"start_date\"></p>
            '''

    form += f'''
                <p><label for=\"end_date\">Конец (ГГГГ-ММ-ДД)</label>
                <input type=\"text\" name=\"end_date\"></p>
            '''

    form += f'<input type=\"hidden\" name=\"weekday\" value=\"{weekDay}\">'
    form += f'<input type=\"hidden\" name=\"pair_number\" value=\"{pairNumber}\">'
    form += f'<input type=\"hidden\" name=\"recurrence\" value=\"weekly\">'

    form += '<p><label for="week_parity">Числитель/Знаменатель</label>'
    form += '<select name="week_parity">'
    form += '<option value="" selected disabled>Выберите неделю</option>'
    form += '<option value="even">Числитель</option>'
    form += '<option value="odd">Знаменатель</option>'
    form += '</select></p>'

    return form


def lessonsPage(request):
    HTMLtimeTable = ''
    form = ''
    if request.method == "GET":
        group = GETGroup(request)
        if group is not None:
            HTMLtimeTable = generateHTMLTimeTable(group)
            id = GETId(request)
            weekDay = GETWeekDay(request)
            pairNumber = GETPairNumber(request)

            if id:
                pass
            elif weekDay and pairNumber:
                form = generateFormForNewLesson(group, weekDay, pairNumber)

    if request.method == "POST":
        keys = []
        values = []
        for key, value in request.POST.items():
            if key == 'csrfmiddlewaretoken':
                continue

            if value == '':
                values.append('NULL')
            else:
                values.append(f"\'{value}\'")
            keys.append(key)

        with connection.cursor() as cursor:
            query = f'INSERT INTO lessons ({", ".join(keys)}) VALUES ({", ".join(values)})'
            print(query)
            cursor.execute(query)
        group = GETGroup(request)
        query_params = urlencode({'groupId': group})
        return redirect(f"{request.path}?{query_params}")

    groupList = generateGroupList()
    renderPage = render(request, 'main/lessons.html',
                        {'tablelistGen': mark_safe(groupList), 'table': mark_safe(HTMLtimeTable), 'form': mark_safe(form)})

    return renderPage