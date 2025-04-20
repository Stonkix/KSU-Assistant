from django.shortcuts import render, redirect
from django.http import HttpResponse
from django import forms
from django.db import connection
from django.utils.safestring import mark_safe
from urllib.parse import urlencode

primary_keys = [
    'id',
    'user_id',
    'pair_number',
]

dictTables = {
    'users': '',
    'students': '',
    'teachers': '',
    'event_participants': '',
    'events': '',
    'academic_groups': '',
    'lessons': '',
    'rooms': '',
    'pair_times': '',
    'subjects': '',
    # 'apartments': 'Жильё',
    # 'gastarbiters': 'Гастарбайтеры',
    # 'Gas_Tools': 'Гастарбайтеры-инструменты',
    # 'owners': 'Хозяева квартир',
    # 'tools': 'Инструменты',
    # 'workplaces': 'Места работы'
}

dictLabels = {
    # 'f_name': 'Фамилия',
    # 'i_name': 'Имя',
    # 'o_name': 'Отчество',
    # 'pasport_ser': 'Серия паспорта',
    # 'pasport_num': 'Номер серии',
    # 'salary': 'Зарплата',
    # 'id_workplace': 'id рабочего места',
    # 'id_apartment': 'id квартиры проживания',
    # 'adress': 'Адрес',
    # 'num_of_rooms': 'Количество комнат',
    # 'id_owner': 'id владельца',
    # 'id_gas': 'id гастарбайтера',
    # 'id_tool': 'id инструмента',
    # 'phone_num': 'Номер телефона',
    # 'email': 'Электронная почта',
    # 'tooltype': 'Тип инструмента',
    # 'disrepair': 'Состояние',
    # 'worktype': 'Задание',
    # 'employer': 'Наниматель',
}

dictUserTypes = {
        'students': '',
        'teachers': '',
    }

# class SimpleForm(forms.Form):
#     name = forms.CharField(label='Имя', max_length=100)
#     age = forms.IntegerField(label='Возраст', min_value=0)
#     email = forms.EmailField(label='Электронная почта')
#     birth_date = forms.DateField(label='Дата рождения', widget=forms.DateInput(attrs={'type': 'date'}))


def GETPrimaryKeyName(table_name):
    with connection.cursor() as cursor:
        # (cid, name, type, notnull, dflt_value, pk)
        query = f"PRAGMA table_info({table_name});"
        cursor.execute(query)
        columns = cursor.fetchall()
        primaryKeyName = columns[0][1]
    return primaryKeyName


def GETTable(request):
    table_name = request.GET.get('table')
    print(f'table: {table_name}')
    return table_name


def GETId(request):
    id = request.GET.get('id')
    if id is not None:
        print(f'id: {id}')
        return id
    return None


def generateTableList():
    tableList = ''
    for table in dictTables:
        if dictTables[table] != '':
            title = dictTables[table]
        else:
            title = table
        string = f'<li><a href="?table={table}"><button>{title}</button></a></li>'
        tableList += string
    return tableList


def generateUserTypesList():
    userTypesList = ''
    for userType in dictUserTypes:
        if dictUserTypes[userType] != '':
            title = dictUserTypes[userType]
        else:
            title = userType
        string = f'<li><a href="?userType={userType}"><button>{title}</button></a></li>'
        userTypesList += string
    return userTypesList


def generateForm(table_name):
    form = ""
    with connection.cursor() as cursor:
        # (cid, name, type, notnull, dflt_value, pk)
        # query = f"""
        # SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        # FROM INFORMATION_SCHEMA.COLUMNS
        # WHERE TABLE_NAME = '{table_name}'
        # """
        query = f"PRAGMA table_info({table_name});"
        cursor.execute(query)
        columns = cursor.fetchall()

    form += f'<input type=\"hidden\" name=\"table\" value=\"{table_name}\">'

    for column in columns:
        key = column[1]
        if key == 'id':
            continue
        if key in dictLabels:
            title = dictLabels[key]
        else:
            title = key
        column = f'''
            <p><label for=\"{key}\">{title}</label>
            <input type=\"text\" name=\"{key}\"></p>
        '''
        form += column
    return mark_safe(form)


def generateFilledForm(table_name, id):
    primaryKeyName = GETPrimaryKeyName(table_name)
    form = ""
    with connection.cursor() as cursor:
        # (cid, name, type, notnull, dflt_value, pk)
        # query = f"""
        # SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        # FROM INFORMATION_SCHEMA.COLUMNS
        # WHERE TABLE_NAME = '{table_name}'
        # """
        query = f"PRAGMA table_info({table_name});"
        cursor.execute(query)
        columns = cursor.fetchall()

        query = f"""
        SELECT *
        FROM {table_name}
        WHERE {primaryKeyName} = {id}
        """
        cursor.execute(query)
        row = cursor.fetchall()

        print(f'columns: {columns}')

    form += f'<input type=\"hidden\" name=\"table\" value=\"{table_name}\">'
    form += f'<input type=\"hidden\" name=\"id\" value=\"{id}\">'

    for i in range(len(columns)): # key, type, length
        key = columns[i][1]
        # type = columns[i][2]
        # length = columns[i][2]
        value = row[0][i]

        if key == 'id':
            continue
        if key in dictLabels:
            title = dictLabels[key]
        else:
            title = key

        if value is None:
            value = ''

        column = f'''
            <p><label for=\"{key}\">{title}</label>
            <input type=\"text\" name=\"{key}\" value=\"{value}\"></p>
        '''
        form += column
    return mark_safe(form)


def generateFormToDelete(table_name, id):
    primaryKeyName = GETPrimaryKeyName(table_name)

    form = ''

    form += f'<input type=\"hidden\" name=\"table\" value=\"{table_name}\">'
    form += f'<input type=\"hidden\" name=\"{primaryKeyName}\" value=\"{id}\">'

    form += f'<p>Точно удалить из таблицы {dictTables[table_name]} запись с {primaryKeyName} {id}?</p>'
    return form


def generateFormForNewStudent():
    dictColumns = {
        'email': 'Почта',
        'password': 'Пароль',
        'full_name': 'Полное ФИО',
    }

    with connection.cursor() as cursor:
        query = f"""
        SELECT *
        FROM academic_groups
        """
        cursor.execute(query)
        groups = cursor.fetchall()

    form = ''
    form += f'<input type=\"hidden\" name=\"role\" value=\"student\">'
    form += f'<input type=\"hidden\" name=\"role\" value=\"student\">'

    for columnName in dictColumns:
        column = f'''
                <p><label for=\"{columnName}\">{dictColumns[columnName]}</label>
                <input type=\"text\" name=\"{columnName}\"></p>
            '''
        form += column

    form += '<p><label for="group_id">Академическая группа</label>'
    form += '<select name="group_id">'
    form += '<option value="" selected disabled>Выберите группу</option>'
    for group_id, group_name in groups:
        form += f'<option value="{group_id}">{group_name}</option>'
    form += '</select></p>'
    return form


def generateFormForNewTeacher():
    form = ''
    return form


def generateHTMLTable(table_name):
    table = ""
    with connection.cursor() as cursor:
        # (cid, name, type, notnull, dflt_value, pk)
        query = f"PRAGMA table_info({table_name});"
        cursor.execute(query)
        columns = cursor.fetchall()
    table = '<tr>'
    for column in columns:
        table += f'<td>{column[1]}</td>'
    table += '</tr>'
    print(table)
    with connection.cursor() as cursor:
        query = f"""
        SELECT *
        FROM {table_name}
        """
        cursor.execute(query)
        rows = cursor.fetchall()

    for row in rows:
        HTMLRow = f'<tr id={row[0]}>'
        for column in row:
            HTMLRow += f'<td>{column}</td>'
        HTMLRow += '</tr>'
        table += HTMLRow

    return table

# Create your views here.

def index(req):
    return render(req, 'main/index.html')

def testPage(request):
    table = ''
    form = generateForm(table)
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
            query = f'INSERT INTO {table} ({", ".join(keys)}) VALUES ({", ".join(values)})'
            print(query)
            cursor.execute(query)

        query_params = urlencode({'table': table, 'id': id})
        return redirect(f"{request.path}?{query_params}")
    return render(request, 'main/test.html', {'form': mark_safe(form)})


def GETUserType(request):
    userType = request.GET.get('userType')
    if userType is not None:
        print(f'userType: {userType}')
        return userType
    return None


def newUserPage(request):
    form = ''

    if request.method == "GET":
        userType = GETUserType(request)
        if userType is not None:
            if userType == 'students':
                form = generateFormForNewStudent()
            elif userType == 'teachers':
                form = generateFormForNewTeacher()

    elif request.method == "POST":
        keys = []
        values = []
        for key, value in request.POST.items():
            print(f'POST {key, value}')
            if key == 'csrfmiddlewaretoken':
                continue
            if key == 'password':
                keys.append('password_hash')

        # with connection.cursor() as cursor:
        #     query = f'INSERT INTO users ({", ".join(keys)}) VALUES ({", ".join(values)})'
        #     print(query)
        #     cursor.execute(query)

    userTypesList = generateUserTypesList()
    renderPage = render(request, 'main/add user.html', {'tablelistGen': mark_safe(userTypesList), 'form': mark_safe(form)})

    return renderPage


def viewPage(request):
    table = ''
    HTMLTable = ''

    if request.method == "GET":
        table = GETTable(request)
        print(f'_{table}_')
        if table is not None:
            HTMLTable = generateHTMLTable(table)

    tableList = generateTableList()
    renderPage = render(request, 'main/view.html', {'tablelistGen': mark_safe(tableList), 'table': mark_safe(HTMLTable)})

    return renderPage


def changePage(request):
    table = ''
    HTMLTable = ''
    form = ''

    if request.method == "GET":
        table = GETTable(request)
        id = GETId(request)
        if table is not None:
            HTMLTable = generateHTMLTable(table)

            if id is not None:
                form = generateFilledForm(table, id)

    elif request.method == "POST":
        keys = []
        values = []
        primaryKeyName = ''
        for key, value in request.POST.items():
            if key == 'table':
                table = value
                continue
            if key in primary_keys:
                id = value
                primaryKeyName = key
                continue

            if key == 'csrfmiddlewaretoken':
                continue

            if value == '':
                values.append('NULL')
            else:
                values.append(f"\'{value}\'")

            keys.append(key)
        with connection.cursor() as cursor:
            lstValues = []
            for i in range(len(keys)):
                lstValues.append(f'{keys[i]} = {values[i]}')
            query = f'UPDATE {table} SET {", ".join(lstValues)}  WHERE {primaryKeyName} = {id}'
            print(query)
            cursor.execute(query)

        query_params = urlencode({'table': table, 'id': id})
        return redirect(f"{request.path}?{query_params}")

    tableList = generateTableList()
    renderPage = render(request, 'main/change.html', {'tablelistGen': mark_safe(tableList),
                                                      'table': mark_safe(HTMLTable),
                                                      'form': mark_safe(form)})

    return renderPage


def addPage(request):
    table = ''
    form = ''

    if request.method == "GET":
        table = GETTable(request)
        if table is not None:
            form = generateForm(table)

    if request.method == "POST":
        keys = []
        values = []
        for key, value in request.POST.items():
            if key == 'table':
                table = value
                continue
            # if table == '': # exit
            #     print(f'table {table} g')
            #     return renderPage
            if key == 'csrfmiddlewaretoken':
                continue

            if value == '':
                values.append('NULL')
            else:
                values.append(f"\'{value}\'")

            keys.append(key)
        with connection.cursor() as cursor:
            query = f'INSERT INTO {table} ({", ".join(keys)}) VALUES ({", ".join(values)})'
            print(query)
            cursor.execute(query)

        query_params = urlencode({'table': table})
        return redirect(f"{request.path}?{query_params}")

    tableList = generateTableList()
    renderPage = render(request, 'main/add.html', {'form': mark_safe(form), 'tablelistGen': mark_safe(tableList)})

    return renderPage


def deletePage(request):
    table = ''
    HTMLTable = ''
    form = ''

    if request.method == "GET":
        table = GETTable(request)
        id = GETId(request)
        if table is not None:
            HTMLTable = generateHTMLTable(table)

            if id is not None:
                form = generateFormToDelete(table, id)

    elif request.method == "POST":
        id = ''
        table = ''
        primaryKeyName = ''
        for key, value in request.POST.items():
            if key == 'table':
                table = value
                continue
            if key in primary_keys:
                id = value
                primaryKeyName = key
                continue
            if key == 'csrfmiddlewaretoken':
                continue
        if id != '':
            print(f'delete {table} {id}')
            with connection.cursor() as cursor:
                query = f'DELETE FROM {table} WHERE {primaryKeyName} = {id}'
                print(query)
                cursor.execute(query)

        query_params = urlencode({'table': table, 'id': id})
        return redirect(f"{request.path}?{query_params}")


    tableList = generateTableList()
    renderPage = render(request, 'main/delete.html', {'form': mark_safe(form),
                                                      'tablelistGen': mark_safe(tableList),
                                                      'table': mark_safe(HTMLTable)})

    return renderPage