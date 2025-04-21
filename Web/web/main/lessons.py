from django.shortcuts import render, redirect
from django.http import HttpResponse
from django import forms
from django.db import connection
from django.utils.safestring import mark_safe
from urllib.parse import urlencode

import sys
from pathlib import Path

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

    with connection.cursor() as cursor:
        query = f'SELECT * FROM pair_times'
        print(query)
        cursor.execute(query)
        pairTimes = cursor.fetchall()

    table = ''

    table += '<tr>'
    table += '<td>Время</td>'
    for weekDay in dictWeekDays:
        table += f'<td>{dictWeekDays[weekDay]}</td>'
    table += '</tr>'

    for pair_number, start_time, end_time in pairTimes:
        table += '<tr>'
        table += f'<td>{start_time}-{end_time}</td>'
        for weekDay in dictWeekDays:
            table += f'<td>-</td>'
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