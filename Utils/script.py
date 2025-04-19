import sqlite3

# Создаём подключение к базе данных (создаст файл, если его нет)
conn = sqlite3.connect("university.db")
cursor = conn.cursor()

# Включаем поддержку внешних ключей
cursor.execute("PRAGMA foreign_keys = ON;")

# SQL-схема
schema = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    telegram_id TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student', 'teacher'))
);

CREATE TABLE academic_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE students (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    group_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (group_id) REFERENCES academic_groups(id)
);

CREATE TABLE teachers (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    department TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    teacher_id INTEGER,
    FOREIGN KEY (teacher_id) REFERENCES teachers(user_id)
);

CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT NOT NULL,
    building TEXT NOT NULL
);

CREATE TABLE pair_times (
    pair_number INTEGER PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);

CREATE TABLE lessons (
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

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    datetime TEXT NOT NULL,
    description TEXT,
    target_roles TEXT DEFAULT 'both' CHECK(target_roles IN ('student', 'teacher', 'both')),
    group_id INTEGER,
    FOREIGN KEY (group_id) REFERENCES academic_groups(id)
);

CREATE TABLE event_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'interested' CHECK(status IN ('interested', 'going', 'declined')),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

# Выполняем скрипт
cursor.executescript(schema)

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()

print("База данных успешно создана.")
