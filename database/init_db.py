import sqlite3
import os
import json
from werkzeug.security import generate_password_hash

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = 'school_canteen.db'
DB_PATH = os.path.join(BASE_DIR, DB_NAME)


def create_tables():
    """Создание таблиц users (с аллергенами) и dishes"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Сбрасываем старые таблицы
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS dishes')

    # 1. ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        allergens TEXT,                     -- JSON список аллергенов
        ate_breakfast BOOLEAN DEFAULT 0,
        ate_lunch BOOLEAN DEFAULT 0,
        subscription_days INTEGER DEFAULT 0
    )
    ''')

    # 2. ТАБЛИЦА ЕДЫ
    cursor.execute('''
    CREATE TABLE dishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        image_url TEXT,
        stock_quantity INTEGER DEFAULT 0,
        calories INTEGER,
        ingredients TEXT,
        reviews TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Таблицы созданы в базе: {DB_PATH}")


def seed_data():
    """Заполнение тестовыми данными"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    pass_hash = generate_password_hash('1234')

    # --- Создаем пользователей ---
    # Добавили пустой список аллергенов json.dumps([]) для каждого
    users = [
        # username, email, password, role, allergens, ate_breakfast, ate_lunch, sub_days
        ('Олег Чикушка',          'student@test.ru', pass_hash, 'student', json.dumps([]), 0, 0, 0),
        ('Серёга Нефильтрованное', 'cook@test.ru',    pass_hash, 'cook',    json.dumps([]), 0, 0, 0),
        ('admin',                  'admin@test.ru',   pass_hash, 'admin',   json.dumps([]), 0, 0, 0)
    ]

    cursor.executemany('''
        INSERT INTO users (username, email, password_hash, role, allergens, ate_breakfast, ate_lunch, subscription_days) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', users)
    print("👤 Тестовые пользователи (Олег, Серёга, Admin) добавлены.")

    # --- Создаем блюда ---
    dishes = [
        (
            'Овсяная каша',
            '/assets/goida.jpg',
            50,
            250,
            json.dumps(['Овсяные хлопья', 'Молоко', 'Масло']),
            json.dumps(['нищтяк 2!'])
        ),
        (
            'Борщ',
            '/assets/goida.jpg',
            30,
            350,
            json.dumps(['Свекла', 'Капуста', 'Говядина', 'Сметана']),
            json.dumps(['нищтяк'])
        )
    ]

    cursor.executemany('''
        INSERT INTO dishes (name, image_url, stock_quantity, calories, ingredients, reviews) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', dishes)
    print("🍲 Тестовое меню добавлено.")

    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_tables()
    seed_data()
    print("🚀 База данных готова к работе!")
