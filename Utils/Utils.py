import hashlib

#Функция создания пользователя

#Функция хэширования паролей
def hashPassword(password, salt='*3h%pD?1Cnf-'):
    return hashlib.sha256((password + salt).encode()).hexdigest()

#password = 'sonik' // тут можно ввести свой пароль и получить хэш для бд
#superpassword = hashPassword(password)
#print(superpassword)

#Функция проверки пароля
def verifyPassword(stored_hash, password):
    return stored_hash == hashPassword(password)