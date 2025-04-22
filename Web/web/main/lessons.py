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

                    table += f"""<div class="filled-cell">
                                    {dictSubjects[lesson[1]]}<br>
                                    {dictTeachers[lesson[2]]}<br>
                                    {dictRooms[lesson[4]][0]} к.{dictRooms[lesson[4]][1]}<br>
                                    {dictWeekParity[lesson[-1]]}<br>
                                </div>"""
                    table += '<div class="empty-cell">+</div>'
                table += '</td>'
            else:
                table += '<td>'
                table += '<div class="empty-cell">+</div>'
                table += '</td>'
        table += '</tr>'


    return table

def lessonsPage(request):
    HTMLtimeTable = ''

    if request.method == "GET":
        group = GETGroup(request)
        if group is not None:
            HTMLtimeTable = generateHTMLTimeTable(group)

    elif request.method == "POST":
        pass

    groupList = generateGroupList()
    renderPage = render(request, 'main/lessons.html',
                        {'tablelistGen': mark_safe(groupList), 'table': mark_safe(HTMLtimeTable)})

    return renderPage