import sqlite3
import os
import json
from werkzeug.security import generate_password_hash

# Имя файла базы данных
DB_NAME = 'school_canteen.db'


def create_tables():
    """Создает структуру таблиц (схемы)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ (Users)
    # Обратите внимание: BOOLEAN в SQLite хранится как 0 (False) и 1 (True)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        ate_breakfast BOOLEAN DEFAULT 0,
        ate_lunch BOOLEAN DEFAULT 0,
        subscription_days INTEGER DEFAULT 0
    )
    ''')

    # 2. ТАБЛИЦА ЕДЫ (Dishes)
    # Поля ingredients и reviews храним как TEXT (JSON строка)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dishes (
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
    print("✅ Таблицы 'users' и 'dishes' успешно созданы.")


def seed_data():
    """Заполняет базу начальными данными (чтобы не было пусто)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # --- ДОБАВЛЯЕМ ПОЛЬЗОВАТЕЛЕЙ ---
    # Проверяем, пусто ли в таблице
    cursor.execute('SELECT count(*) FROM users')
    if cursor.fetchone()[0] == 0:
        users = [
            # username, email, password (hashed), role, ate_breakfast, ate_lunch, sub_days
            ('Ivan Student', 'student', generate_password_hash('1234'), 'student', 0, 0, 30),
            ('Maria Cook', 'cook', generate_password_hash('1234'), 'cook', 0, 1, 0),
            ('Chief Admin', 'admin', generate_password_hash('1234'), 'admin', 0, 0, 0)
        ]

        cursor.executemany('''
            INSERT INTO users (username, email, password_hash, role, ate_breakfast, ate_lunch, subscription_days) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', users)
        print("👤 Тестовые пользователи добавлены (пароль 1234).")

    # --- ДОБАВЛЯЕМ ЕДУ ---
    cursor.execute('SELECT count(*) FROM dishes')
    if cursor.fetchone()[0] == 0:
        # Для массивов используем json.dumps
        dishes = [
            (
                'Овсяная каша',
                '/assets/porridge.jpg',
                50,
                250,
                json.dumps(['Овсяные хлопья', 'Молоко', 'Сахар', 'Масло']),
                json.dumps(['Вкусно!', 'Слишком сладко'])
            ),
            (
                'Борщ',
                '/assets/borscht.jpg',
                20,
                350,
                json.dumps(['Свекла', 'Капуста', 'Картофель', 'Говядина']),
                json.dumps(['Как у мамы', 'Мало сметаны'])
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
    # Удаляем старый файл БД, чтобы пересоздать с новой структурой (для разработки)
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print("🗑️ Старая база данных удалена.")
        except PermissionError:
            print("❌ ОШИБКА: Не могу удалить базу. Закройте Flask или DB Browser!")

    create_tables()
    seed_data()
    print(f"🚀 База данных {DB_NAME} готова!")
