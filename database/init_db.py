import sqlite3
import os
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = 'school_canteen.db'
DB_PATH = os.path.join(BASE_DIR, DB_NAME)


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = ['users', 'dishes', 'ingredients', 'dish_ingredients', 'menu',
              'orders', 'payments', 'allergens', 'reviews', 'purchase_requests']
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')

    # 1. Users (ДОБАВЛЕНО ПОЛЕ BALANCE)
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'cook', 'admin')),
        balance DECIMAL(10, 2) DEFAULT 0.00,  -- Баланс кошелька
        subscription_end_date DATE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ... (Остальные таблицы без изменений, копирую для целостности) ...

    cursor.execute(
        'CREATE TABLE dishes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, image_url TEXT, calories INTEGER, current_stock INTEGER DEFAULT 0, price DECIMAL(10, 2) DEFAULT 0.0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute(
        'CREATE TABLE ingredients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, unit TEXT NOT NULL, current_quantity REAL DEFAULT 0, min_quantity REAL DEFAULT 10.0, price_per_unit DECIMAL(10, 2), created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute(
        'CREATE TABLE dish_ingredients (dish_id INTEGER NOT NULL, ingredient_id INTEGER NOT NULL, quantity REAL NOT NULL, PRIMARY KEY (dish_id, ingredient_id), FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE, FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE)')
    cursor.execute(
        'CREATE TABLE menu (id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE NOT NULL, meal_type TEXT NOT NULL CHECK(meal_type IN ("breakfast", "lunch")), dish_id INTEGER NOT NULL, max_portions INTEGER DEFAULT 100, FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE)')
    cursor.execute(
        'CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, menu_id INTEGER NOT NULL, order_date DATETIME DEFAULT CURRENT_TIMESTAMP, paid BOOLEAN DEFAULT 0, collected BOOLEAN DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY (menu_id) REFERENCES menu(id) ON DELETE CASCADE)')

    # Payments (история транзакций)
    cursor.execute('''
    CREATE TABLE payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        type TEXT NOT NULL CHECK(type IN ('subscription', 'single', 'topup')), -- Добавил тип topup
        order_id INTEGER NULL,
        status TEXT DEFAULT 'completed',
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
    )
    ''')

    cursor.execute(
        'CREATE TABLE allergens (user_id INTEGER NOT NULL, ingredient_id INTEGER NOT NULL, note TEXT, PRIMARY KEY (user_id, ingredient_id))')
    cursor.execute(
        'CREATE TABLE reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, dish_id INTEGER NOT NULL, rating INTEGER NOT NULL, comment TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute(
        'CREATE TABLE purchase_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, ingredient_id INTEGER NOT NULL, quantity REAL NOT NULL, requested_by INTEGER NOT NULL, request_date DATETIME DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT "pending", approved_by INTEGER NULL, approved_date DATETIME NULL, notes TEXT)')

    conn.commit()
    conn.close()
    print("✅ Таблицы созданы (balance добавлен).")


def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    pw = generate_password_hash('1234')
    today = datetime.now().date()

    # Пользователи (Дадим студенту 500 рублей на старт)
    users = [
        (1, 'Admin', 'admin@school.ru', pw, 'admin', 0.0, None),
        (2, 'Cook', 'cook@school.ru', pw, 'cook', 0.0, None),
        (3, 'Student', 'student@school.ru', pw, 'student', 500.0, None)  # 500р на счету, без подписки
    ]
    cursor.executemany(
        'INSERT INTO users (id, username, email, password_hash, role, balance, subscription_end_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
        users)
    cursor.execute("UPDATE sqlite_sequence SET seq = 3 WHERE name = 'users'")

    # Ингредиенты
    ingredients = [('Молоко', 'л'), ('Яйца', 'шт'), ('Мука', 'кг'), ('Сахар', 'кг'), ('Соль', 'кг'),
                   ('Картофель', 'кг'), ('Морковь', 'кг'), ('Лук', 'кг'), ('Курица', 'кг'), ('Говядина', 'кг'),
                   ('Рис', 'кг'), ('Гречка', 'кг')]
    cursor.executemany('INSERT INTO ingredients (name, unit, current_quantity) VALUES (?, ?, 100)', ingredients)

    # Блюда
    dishes = [('Омлет', 250, 50, 70), ('Борщ', 300, 40, 120), ('Котлета', 280, 60, 90), ('Гречка', 200, 80, 50),
              ('Рис', 210, 80, 50)]
    cursor.executemany('INSERT INTO dishes (name, calories, current_stock, price) VALUES (?, ?, ?, ?)', dishes)

    # Связи (упрощенно)
    cursor.execute("INSERT INTO dish_ingredients (dish_id, ingredient_id, quantity) VALUES (1, 2, 2)")  # Омлет - Яйца

    # Меню
    dish_map = {name: id for id, name in cursor.execute("SELECT id, name FROM dishes").fetchall()}
    menu = [
        (today.isoformat(), 'breakfast', dish_map['Омлет']),
        (today.isoformat(), 'lunch', dish_map['Борщ']),
        (today.isoformat(), 'lunch', dish_map['Котлета'])
    ]
    cursor.executemany('INSERT INTO menu (date, meal_type, dish_id) VALUES (?, ?, ?)', menu)

    conn.commit()
    conn.close()
    print("👤 Данные загружены. Student баланс: 500р")


if __name__ == '__main__':
    create_tables()
    seed_data()
