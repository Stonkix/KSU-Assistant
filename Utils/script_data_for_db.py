import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('university.db')
cursor = conn.cursor()

# Добавление пользователя
user_data = (
    'EvchukAS@studklg.ru',
    'b727d62f1177969acec739c3228cf2ce52e50047d980661e4ba26f2ee55c85f3',
    'student',
    None  # telegram_id пока пустой
)

cursor.execute("""
INSERT INTO users (email, password_hash, role, telegram_id)
VALUES (?, ?, ?, ?)
""", user_data)

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()

print("Пользователь успешно добавлен в базу данных")