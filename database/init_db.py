import sqlite3
import os
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

DB_NAME = 'school_canteen.db'


def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS dishes')
    cursor.execute('DROP TABLE IF EXISTS ingredients')
    cursor.execute('DROP TABLE IF EXISTS dish_ingredients')
    cursor.execute('DROP TABLE IF EXISTS menu')
    cursor.execute('DROP TABLE IF EXISTS orders')
    cursor.execute('DROP TABLE IF EXISTS payments')
    cursor.execute('DROP TABLE IF EXISTS allergens')
    cursor.execute('DROP TABLE IF EXISTS reviews')
    cursor.execute('DROP TABLE IF EXISTS purchase_requests')

    # 1. Users
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'cook', 'admin')),
        subscription_end_date DATE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Dishes
    cursor.execute('''
    CREATE TABLE dishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        image_url TEXT,
        calories INTEGER,
        current_stock INTEGER DEFAULT 0,
        price DECIMAL(10, 2) DEFAULT 0.0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 3. Ingredients
    cursor.execute('''
    CREATE TABLE ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        unit TEXT NOT NULL,
        current_quantity REAL DEFAULT 0,
        min_quantity REAL DEFAULT 10.0,
        price_per_unit DECIMAL(10, 2),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 4. Dish Ingredients
    cursor.execute('''
    CREATE TABLE dish_ingredients (
        dish_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        PRIMARY KEY (dish_id, ingredient_id),
        FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
    )
    ''')

    # 5. Menu
    cursor.execute('''
    CREATE TABLE menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        meal_type TEXT NOT NULL CHECK(meal_type IN ('breakfast', 'lunch')),
        dish_id INTEGER NOT NULL,
        max_portions INTEGER DEFAULT 100,
        FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE
    )
    ''')

    # 6. Orders
    cursor.execute('''
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        menu_id INTEGER NOT NULL,
        order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        paid BOOLEAN DEFAULT 0,
        collected BOOLEAN DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (menu_id) REFERENCES menu(id) ON DELETE CASCADE
    )
    ''')

    # 7. Payments
    cursor.execute('''
    CREATE TABLE payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        type TEXT NOT NULL CHECK(type IN ('subscription', 'single')),
        order_id INTEGER NULL,
        status TEXT DEFAULT 'completed',
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
    )
    ''')

    # 8. Allergens
    cursor.execute('''
    CREATE TABLE allergens (
        user_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        note TEXT,
        PRIMARY KEY (user_id, ingredient_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
    )
    ''')

    # 9. Reviews
    cursor.execute('''
    CREATE TABLE reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        dish_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
        comment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE
    )
    ''')

    # 10. Purchase Requests
    cursor.execute('''
    CREATE TABLE purchase_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingredient_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        requested_by INTEGER NOT NULL,
        request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        approved_by INTEGER NULL,
        approved_date DATETIME NULL,
        notes TEXT,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
        FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    conn.close()
    print("✅ Таблицы созданы.")


def seed_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Users
    today = datetime.now().date()
    # Пароль: 1234
    pw = generate_password_hash('1234')

    users = [
        ('student', 'student@school.ru', pw, 'student', (today + timedelta(days=30)).isoformat()),
        ('cook', 'cook@school.ru', pw, 'cook', None),
        ('admin', 'admin@school.ru', pw, 'admin', None),
    ]
    cursor.executemany(
        'INSERT INTO users (username, email, password_hash, role, subscription_end_date) VALUES (?, ?, ?, ?, ?)', users)

    # 2. Ingredients (Аллергены)
    ingredients = [
        ('Молоко', 'л'), ('Яйца', 'шт'), ('Мука', 'кг'), ('Сахар', 'кг'),
        ('Соль', 'кг'), ('Картофель', 'кг'), ('Морковь', 'кг'), ('Лук', 'кг'),
        ('Курица', 'кг'), ('Говядина', 'кг'), ('Рис', 'кг'), ('Гречка', 'кг')
    ]
    cursor.executemany('INSERT INTO ingredients (name, unit, current_quantity) VALUES (?, ?, 100)', ingredients)

    # Получаем ID ингредиентов для связей
    cursor.execute('SELECT id, name FROM ingredients')
    ing_map = {name: id for id, name in cursor.fetchall()}

    # 3. Dishes
    dishes = [
        ('Омлет', 250, 50, 70),
        ('Борщ', 300, 40, 120),
        ('Котлета куриная', 280, 60, 90),
        ('Гречка', 200, 80, 50),
        ('Рис', 210, 80, 50)
    ]
    cursor.executemany('INSERT INTO dishes (name, calories, current_stock, price) VALUES (?, ?, ?, ?)', dishes)

    # Получаем ID блюд
    cursor.execute('SELECT id, name FROM dishes')
    dish_map = {name: id for id, name in cursor.fetchall()}

    # 4. Dish Ingredients (Состав)
    # Омлет: Яйца, Молоко
    cursor.execute('INSERT INTO dish_ingredients (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)',
                   (dish_map['Омлет'], ing_map['Яйца'], 2))
    cursor.execute('INSERT INTO dish_ingredients (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)',
                   (dish_map['Омлет'], ing_map['Молоко'], 0.1))

    # Борщ: Говядина, Картофель, Морковь
    cursor.execute('INSERT INTO dish_ingredients (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)',
                   (dish_map['Борщ'], ing_map['Говядина'], 0.1))
    cursor.execute('INSERT INTO dish_ingredients (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)',
                   (dish_map['Борщ'], ing_map['Картофель'], 0.2))

    # Котлета: Курица, Лук
    cursor.execute('INSERT INTO dish_ingredients (dish_id, ingredient_id, quantity) VALUES (?, ?, ?)',
                   (dish_map['Котлета куриная'], ing_map['Курица'], 0.15))

    # 5. Menu (На сегодня)
    menu = [
        (today.isoformat(), 'breakfast', dish_map['Омлет']),
        (today.isoformat(), 'lunch', dish_map['Борщ']),
        (today.isoformat(), 'lunch', dish_map['Котлета куриная']),
        (today.isoformat(), 'lunch', dish_map['Гречка']),
    ]
    cursor.executemany('INSERT INTO menu (date, meal_type, dish_id) VALUES (?, ?, ?)', menu)

    # ЗАКАЗЫ НЕ СОЗДАЕМ! (История будет пустой)

    conn.commit()
    conn.close()
    print("✅ База сброшена. Пользователи: student/1234, cook/1234, admin/1234")


if __name__ == '__main__':
    create_tables()
    seed_data()
