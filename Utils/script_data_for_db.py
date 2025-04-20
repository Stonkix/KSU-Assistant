import sqlite3

# Подключение к базе данных (создаст файл university.db)
conn = sqlite3.connect("university.db")
cursor = conn.cursor()

# Схема базы данных
schema = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    telegram_id TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student', 'teacher'))
);

CREATE TABLE IF NOT EXISTS academic_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    group_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (group_id) REFERENCES academic_groups(id)
);

CREATE TABLE IF NOT EXISTS teachers (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    department TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    teacher_id INTEGER,
    FOREIGN KEY (teacher_id) REFERENCES teachers(user_id)
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT NOT NULL,
    building TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pair_times (
    pair_number INTEGER PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    weekday INTEGER NOT NULL,
    pair_number INTEGER NOT NULL,
    recurrence TEXT,
    week_parity TEXT,
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(user_id),
    FOREIGN KEY (group_id) REFERENCES academic_groups(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (pair_number) REFERENCES pair_times(pair_number)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    datetime TEXT NOT NULL,
    description TEXT,
    target_roles TEXT DEFAULT 'both' CHECK(target_roles IN ('student', 'teacher', 'both')),
    group_id INTEGER,
    FOREIGN KEY (group_id) REFERENCES academic_groups(id)
);

CREATE TABLE IF NOT EXISTS event_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'interested' CHECK(status IN ('interested', 'going', 'declined')),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

# Выполнение схемы
cursor.executescript(schema)

# Вставка пользователей (кроме user_id = 1), с защитой от дубликатов
users = [
    ('EvchukAS@studklg.ru', '', 'b727d62f1177969acec739c3228cf2ce52e50047d980661e4ba26f2ee55c85f3', 'student'),
    ('student1@studklg.ru', 'tg_student1', 'hash1', 'student'),
    ('student2@studklg.ru', 'tg_student2', 'hash2', 'student'),
    ('teacher1@studklg.ru', 'tg_teacher1', 'hash3', 'teacher'),
    ('teacher2@studklg.ru', 'tg_teacher2', 'hash4', 'teacher'),
    ('teacher3@example.com', 'tg_teacher3', 'hash5', 'teacher'),
    ('teacher4@example.com', 'tg_teacher4', 'hash6', 'teacher'),
    ('student3@example.com', 'tg_student3', 'hash7', 'student'),
    ('student4@example.com', 'tg_student4', 'hash8', 'student'),
]
cursor.executemany("INSERT OR IGNORE INTO users (email, telegram_id, password_hash, role) VALUES (?, ?, ?, ?)", users)

# Получение ID пользователей
def get_user_id(email):
    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
    row = cursor.fetchone()
    return row[0] if row else None

# Получаем ID для пользователей
evchuk_id = get_user_id('EvchukAS@studklg.ru')
student1_id = get_user_id('student1@example.com')
student2_id = get_user_id('student2@example.com')
teacher1_id = get_user_id('teacher1@example.com')
teacher2_id = get_user_id('teacher2@example.com')
teacher3_id = get_user_id('teacher3@example.com')
teacher4_id = get_user_id('teacher4@example.com')

# Группы
cursor.execute("INSERT OR IGNORE INTO academic_groups (name) VALUES ('Group A')")
cursor.execute("INSERT OR IGNORE INTO academic_groups (name) VALUES ('Group B')")
cursor.execute("INSERT OR IGNORE INTO academic_groups (name) VALUES ('Group C')")

cursor.execute("SELECT id FROM academic_groups WHERE name='Group A'")
group_a_id = cursor.fetchone()[0]
cursor.execute("SELECT id FROM academic_groups WHERE name='Group B'")
group_b_id = cursor.fetchone()[0]
cursor.execute("SELECT id FROM academic_groups WHERE name='Group C'")
group_c_id = cursor.fetchone()[0]

# Студенты
if evchuk_id:
    cursor.execute("INSERT OR IGNORE INTO students (user_id, full_name, group_id) VALUES (?, ?, ?)",
                   (evchuk_id, 'Евчук Александр', group_a_id))
if student1_id:
    cursor.execute("INSERT OR IGNORE INTO students (user_id, full_name, group_id) VALUES (?, ?, ?)",
                   (student1_id, 'Иванов Иван Иванович', group_a_id))
if student2_id:
    cursor.execute("INSERT OR IGNORE INTO students (user_id, full_name, group_id) VALUES (?, ?, ?)",
                   (student2_id, 'Петрова Мария Сергеевна', group_b_id))

# Преподаватели
if teacher1_id:
    cursor.execute("INSERT OR IGNORE INTO teachers (user_id, full_name, department) VALUES (?, ?, ?)",
                   (teacher1_id, 'Сидоров Алексей Николаевич', 'Математика'))
if teacher2_id:
    cursor.execute("INSERT OR IGNORE INTO teachers (user_id, full_name, department) VALUES (?, ?, ?)",
                   (teacher2_id, 'Кузнецова Елена Владимировна', 'Физика'))
if teacher3_id:
    cursor.execute("INSERT OR IGNORE INTO teachers (user_id, full_name, department) VALUES (?, ?, ?)",
                   (teacher3_id, 'Шмидт Андрей Павлович', 'Химия'))
if teacher4_id:
    cursor.execute("INSERT OR IGNORE INTO teachers (user_id, full_name, department) VALUES (?, ?, ?)",
                   (teacher4_id, 'Дмитриев Виктор Сергеевич', 'Литература'))

# Предметы
cursor.execute("INSERT OR IGNORE INTO subjects (name, teacher_id) VALUES (?, ?)", ('Алгебра', teacher1_id))
cursor.execute("INSERT OR IGNORE INTO subjects (name, teacher_id) VALUES (?, ?)", ('Физика', teacher2_id))
cursor.execute("INSERT OR IGNORE INTO subjects (name, teacher_id) VALUES (?, ?)", ('Химия', teacher3_id))
cursor.execute("INSERT OR IGNORE INTO subjects (name, teacher_id) VALUES (?, ?)", ('Литература', teacher4_id))

# Комнаты
cursor.execute("INSERT OR IGNORE INTO rooms (room_number, building) VALUES ('101', 'Корпус 1')")
cursor.execute("INSERT OR IGNORE INTO rooms (room_number, building) VALUES ('202', 'Корпус 2')")
cursor.execute("INSERT OR IGNORE INTO rooms (room_number, building) VALUES ('303', 'Корпус 3')")

# Пары
pair_times = [
    (1, '08:30', '10:00'),
    (2, '10:10', '11:40'),
    (3, '11:50', '13:20'),
    (4, '14:00', '15:30')
]
cursor.executemany("INSERT OR IGNORE INTO pair_times (pair_number, start_time, end_time) VALUES (?, ?, ?)", pair_times)

# Уроки
def get_id_by_query(query, value):
    cursor.execute(query, (value,))
    row = cursor.fetchone()
    return row[0] if row else None

algebra_id = get_id_by_query("SELECT id FROM subjects WHERE name=?", 'Алгебра')
physics_id = get_id_by_query("SELECT id FROM subjects WHERE name=?", 'Физика')
chemistry_id = get_id_by_query("SELECT id FROM subjects WHERE name=?", 'Химия')
literature_id = get_id_by_query("SELECT id FROM subjects WHERE name=?", 'Литература')

room1_id = get_id_by_query("SELECT id FROM rooms WHERE room_number=?", '101')
room2_id = get_id_by_query("SELECT id FROM rooms WHERE room_number=?", '202')
room3_id = get_id_by_query("SELECT id FROM rooms WHERE room_number=?", '303')

if algebra_id and teacher1_id and group_a_id and room1_id:
    cursor.execute("""
        INSERT OR IGNORE INTO lessons (subject_id, teacher_id, group_id, room_id, start_date, end_date, weekday, pair_number, recurrence, week_parity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (algebra_id, teacher1_id, group_a_id, room1_id, '2024-09-01', '2024-12-31', 1, 1, 'weekly', 'odd'))

if physics_id and teacher2_id and group_b_id and room2_id:
    cursor.execute("""
        INSERT OR IGNORE INTO lessons (subject_id, teacher_id, group_id, room_id, start_date, end_date, weekday, pair_number, recurrence, week_parity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (physics_id, teacher2_id, group_b_id, room2_id, '2025-04-20', '2025-05-22', 3, 2, 'weekly', 'even'))

if chemistry_id and teacher3_id and group_c_id and room3_id:
    cursor.execute("""
        INSERT OR IGNORE INTO lessons (subject_id, teacher_id, group_id, room_id, start_date, end_date, weekday, pair_number, recurrence, week_parity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (chemistry_id, teacher3_id, group_c_id, room3_id, '2025-04-20', '2025-05-22', 2, 3, 'weekly', 'odd'))

if literature_id and teacher4_id and group_a_id and room1_id:
    cursor.execute("""
        INSERT OR IGNORE INTO lessons (subject_id, teacher_id, group_id, room_id, start_date, end_date, weekday, pair_number, recurrence, week_parity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (literature_id, teacher4_id, group_a_id, room1_id, '2025-04-20', '2025-05-22', 4, 4, 'weekly', 'even'))

# События
cursor.execute("""
    INSERT OR IGNORE INTO events (title, datetime, description, target_roles, group_id)
    VALUES (?, ?, ?, ?, ?)
""", ('День открытых дверей', '2025-04-20 12:00:00', 'Приглашаем всех!', 'both', None))

cursor.execute("""
    INSERT OR IGNORE INTO events (title, datetime, description, target_roles, group_id)
    VALUES (?, ?, ?, ?, ?)
""", ('Собрание группы A', '2025-04-20 14:00:00', 'Организационное собрание', 'student', group_a_id))

# Участники событий
event1_id = get_id_by_query("SELECT id FROM events WHERE title=?", 'День открытых дверей')
event2_id = get_id_by_query("SELECT id FROM events WHERE title=?", 'Собрание группы A')

if event1_id and student1_id:
    cursor.execute("INSERT OR IGNORE INTO event_participants (event_id, user_id, status) VALUES (?, ?, ?)",
                   (event1_id, student1_id, 'going'))
if event1_id and student2_id:
    cursor.execute("INSERT OR IGNORE INTO event_participants (event_id, user_id, status) VALUES (?, ?, ?)",
                   (event1_id, student2_id, 'interested'))
if event2_id and student1_id:
    cursor.execute("INSERT OR IGNORE INTO event_participants (event_id, user_id, status) VALUES (?, ?, ?)",
                   (event2_id, student1_id, 'going'))

# Сохранение и завершение
conn.commit()
conn.close()
print("✅ База данных успешно создана и заполнена.")
