import sqlite3
import os
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Имя файла базы данных
DB_NAME = 'school_canteen.db'


def create_tables():
    """Создает полную структуру таблиц для школьной столовой"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ (Users)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'cook', 'admin')),
        subscription_end_date DATE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. ТАБЛИЦА БЛЮД (Dishes)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dishes (
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

    # 3. ТАБЛИЦА ИНГРЕДИЕНТОВ (Ingredients)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        unit TEXT NOT NULL,
        current_quantity REAL DEFAULT 0,
        min_quantity REAL DEFAULT 10.0,
        price_per_unit DECIMAL(10, 2),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 4. СВЯЗЬ БЛЮД И ИНГРЕДИЕНТОВ (Dish Ingredients)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dish_ingredients (
        dish_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        PRIMARY KEY (dish_id, ingredient_id),
        FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
    )
    ''')

    # 5. ТАБЛИЦА МЕНЮ (Menu) - расписание блюд по дням
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        meal_type TEXT NOT NULL CHECK(meal_type IN ('breakfast', 'lunch')),
        dish_id INTEGER NOT NULL,
        max_portions INTEGER DEFAULT 100,
        FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE
    )
    ''')

    # 6. ТАБЛИЦА ЗАКАЗОВ/ВЫДАЧИ (Orders)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
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

    # 7. ТАБЛИЦА ПЛАТЕЖЕЙ (Payments)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
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

    # 8. ТАБЛИЦА АЛЛЕРГЕНОВ/ПРЕДПОЧТЕНИЙ (Allergens)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS allergens (
        user_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        note TEXT,
        PRIMARY KEY (user_id, ingredient_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
    )
    ''')

    # 9. ТАБЛИЦА ОТЗЫВОВ (Reviews)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
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

    # 10. ТАБЛИЦА ЗАЯВОК НА ЗАКУПКУ (Purchase Requests)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchase_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingredient_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        requested_by INTEGER NOT NULL,
        request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'completed')),
        approved_by INTEGER NULL,
        approved_date DATETIME NULL,
        notes TEXT,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
        FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # Индексы для ускорения поиска
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user_date ON orders(user_id, order_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_menu_date_type ON menu(date, meal_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_user_date ON payments(user_id, payment_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchase_requests_status ON purchase_requests(status)')

    conn.commit()
    conn.close()
    print("✅ Все таблицы успешно созданы.")


def seed_data():
    """Заполняет базу начальными тестовыми данными"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # --- 1. ПОЛЬЗОВАТЕЛИ ---
    cursor.execute('SELECT count(*) FROM users')
    if cursor.fetchone()[0] == 0:
        today = datetime.now().date()
        users = [
            # username, email, password, role, subscription_end_date
            ('Иван Петров', 'student@school.ru', generate_password_hash('1234'), 'student',
             (today + timedelta(days=30)).isoformat()),
            ('Мария Сидорова', 'student2@school.ru', generate_password_hash('1234'), 'student', None),
            ('Повар Василий', 'cook@school.ru', generate_password_hash('1234'), 'cook', None),
            ('Админ Анна', 'admin@school.ru', generate_password_hash('1234'), 'admin', None),
        ]

        cursor.executemany('''
            INSERT INTO users (username, email, password_hash, role, subscription_end_date) 
            VALUES (?, ?, ?, ?, ?)
        ''', users)
        print("👤 Тестовые пользователи добавлены (пароль 1234).")

    # --- 2. ИНГРЕДИЕНТЫ ---
    cursor.execute('SELECT count(*) FROM ingredients')
    if cursor.fetchone()[0] == 0:
        ingredients = [
            # name, unit, current_quantity, min_quantity, price_per_unit
            ('Картофель', 'кг', 50.0, 10.0, 40.0),
            ('Морковь', 'кг', 20.0, 5.0, 60.0),
            ('Лук', 'кг', 15.0, 3.0, 50.0),
            ('Говядина', 'кг', 30.0, 5.0, 400.0),
            ('Курица', 'кг', 25.0, 5.0, 250.0),
            ('Рис', 'кг', 40.0, 10.0, 80.0),
            ('Гречка', 'кг', 35.0, 8.0, 90.0),
            ('Молоко', 'л', 60.0, 20.0, 70.0),
            ('Яйца', 'шт', 200.0, 50.0, 10.0),
            ('Масло сливочное', 'кг', 10.0, 2.0, 300.0),
            ('Сахар', 'кг', 30.0, 5.0, 60.0),
            ('Соль', 'кг', 20.0, 2.0, 20.0),
        ]

        cursor.executemany('''
            INSERT INTO ingredients (name, unit, current_quantity, min_quantity, price_per_unit)
            VALUES (?, ?, ?, ?, ?)
        ''', ingredients)
        print("🥕 Ингредиенты добавлены.")

    # --- 3. БЛЮДА ---
    cursor.execute('SELECT count(*) FROM dishes')
    if cursor.fetchone()[0] == 0:
        dishes = [
            # name, description, image_url, calories, current_stock, price
            ('Борщ', 'Наваристый борщ с говядиной и сметаной', '/assets/borscht.jpg', 350, 45, 120.0),
            ('Картофельное пюре', 'Нежное пюре с маслом', '/assets/puree.jpg', 250, 60, 80.0),
            ('Куриные котлеты', 'Котлеты из куриного филе', '/assets/cutlets.jpg', 300, 50, 100.0),
            ('Гречневая каша', 'Гречка с маслом', '/assets/grechka.jpg', 200, 70, 60.0),
            ('Омлет', 'Омлет с молоком', '/assets/omelet.jpg', 280, 40, 70.0),
            ('Суп куриный', 'Куриный суп с лапшой', '/assets/chicken_soup.jpg', 320, 30, 90.0),
            ('Рисовая каша', 'Рисовая каша молочная', '/assets/rice_porridge.jpg', 230, 55, 65.0),
            ('Салат овощной', 'Свежие овощи', '/assets/salad.jpg', 150, 40, 50.0),
        ]

        cursor.executemany('''
            INSERT INTO dishes (name, description, image_url, calories, current_stock, price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', dishes)
        print("🍲 Блюда добавлены.")

    # --- 4. СВЯЗЬ БЛЮД И ИНГРЕДИЕНТОВ ---
    cursor.execute('SELECT count(*) FROM dish_ingredients')
    if cursor.fetchone()[0] == 0:
        # Получаем ID блюд и ингредиентов
        cursor.execute("SELECT id, name FROM dishes")
        dish_map = {name: id for id, name in cursor.fetchall()}

        cursor.execute("SELECT id, name FROM ingredients")
        ing_map = {name: id for id, name in cursor.fetchall()}

        # Связываем блюда с ингредиентами (примерные рецепты)
        dish_ingredients = [
            # Борщ
            (dish_map['Борщ'], ing_map['Картофель'], 0.2),
            (dish_map['Борщ'], ing_map['Морковь'], 0.1),
            (dish_map['Борщ'], ing_map['Лук'], 0.05),
            (dish_map['Борщ'], ing_map['Говядина'], 0.15),
            (dish_map['Борщ'], ing_map['Соль'], 0.01),
            # Картофельное пюре
            (dish_map['Картофельное пюре'], ing_map['Картофель'], 0.3),
            (dish_map['Картофельное пюре'], ing_map['Молоко'], 0.05),
            (dish_map['Картофельное пюре'], ing_map['Масло сливочное'], 0.02),
            (dish_map['Картофельное пюре'], ing_map['Соль'], 0.005),
            # Куриные котлеты
            (dish_map['Куриные котлеты'], ing_map['Курица'], 0.2),
            (dish_map['Куриные котлеты'], ing_map['Лук'], 0.03),
            (dish_map['Куриные котлеты'], ing_map['Яйца'], 0.3),
            # Омлет
            (dish_map['Омлет'], ing_map['Яйца'], 2.0),
            (dish_map['Омлет'], ing_map['Молоко'], 0.05),
            (dish_map['Омлет'], ing_map['Соль'], 0.005),
        ]

        cursor.executemany('''
            INSERT INTO dish_ingredients (dish_id, ingredient_id, quantity)
            VALUES (?, ?, ?)
        ''', dish_ingredients)
        print("🔗 Связи блюд и ингредиентов созданы.")

    # --- 5. МЕНЮ НА БЛИЖАЙШИЕ ДНИ ---
    cursor.execute('SELECT count(*) FROM menu')
    if cursor.fetchone()[0] == 0:
        today = datetime.now().date()

        # Получаем ID блюд
        cursor.execute("SELECT id, name FROM dishes")
        dish_ids = {name: id for id, name in cursor.fetchall()}

        menu_items = []

        # Создаем меню на 3 дня вперед
        for day_offset in range(3):
            date_str = (today + timedelta(days=day_offset)).isoformat()

            # Завтрак
            menu_items.append((date_str, 'breakfast', dish_ids['Омлет'], 100))
            menu_items.append((date_str, 'breakfast', dish_ids['Рисовая каша'], 100))

            # Обед
            menu_items.append((date_str, 'lunch', dish_ids['Борщ'], 80))
            menu_items.append((date_str, 'lunch', dish_ids['Куриные котлеты'], 80))
            menu_items.append((date_str, 'lunch', dish_ids['Картофельное пюре'], 80))
            menu_items.append((date_str, 'lunch', dish_ids['Салат овощной'], 80))

        cursor.executemany('''
            INSERT INTO menu (date, meal_type, dish_id, max_portions)
            VALUES (?, ?, ?, ?)
        ''', menu_items)
        print("📅 Меню на 3 дня создано.")

    # --- 6. ТЕСТОВЫЕ ЗАКАЗЫ НА СЕГОДНЯ ---
    cursor.execute('SELECT count(*) FROM orders')
    if cursor.fetchone()[0] == 0:
        # Получаем ID пользователя-студента и меню на сегодня
        cursor.execute("SELECT id FROM users WHERE role = 'student' LIMIT 1")
        student_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM menu WHERE date = date('now') AND meal_type = 'breakfast' LIMIT 1")
        breakfast_menu = cursor.fetchone()

        cursor.execute("SELECT id FROM menu WHERE date = date('now') AND meal_type = 'lunch' LIMIT 1")
        lunch_menu = cursor.fetchone()

        if student_id and breakfast_menu:
            cursor.execute('''
                INSERT INTO orders (user_id, menu_id, paid, collected)
                VALUES (?, ?, 1, 1)
            ''', (student_id, breakfast_menu[0]))

        if student_id and lunch_menu:
            cursor.execute('''
                INSERT INTO orders (user_id, menu_id, paid, collected)
                VALUES (?, ?, 1, 0)
            ''', (student_id, lunch_menu[0]))

        print("📝 Тестовые заказы добавлены.")

    # --- 7. ТЕСТОВЫЕ ПЛАТЕЖИ ---
    cursor.execute('SELECT count(*) FROM payments')
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM users WHERE role = 'student' LIMIT 1")
        student_id = cursor.fetchone()[0]

        if student_id:
            # Платеж за абонемент
            cursor.execute('''
                INSERT INTO payments (user_id, amount, type, status)
                VALUES (?, ?, 'subscription', 'completed')
            ''', (student_id, 1500.0))

            # Получаем ID заказа для разового платежа
            cursor.execute("SELECT id FROM orders WHERE user_id = ? LIMIT 1", (student_id,))
            order_id = cursor.fetchone()

            if order_id:
                cursor.execute('''
                    INSERT INTO payments (user_id, amount, type, order_id, status)
                    VALUES (?, ?, 'single', ?, 'completed')
                ''', (student_id, 120.0, order_id[0]))

            print("💰 Тестовые платежи добавлены.")

    # --- 8. ТЕСТОВЫЕ АЛЛЕРГЕНЫ ---
    cursor.execute('SELECT count(*) FROM allergens')
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM users WHERE role = 'student' LIMIT 1")
        student_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM ingredients WHERE name IN ('Молоко', 'Яйца')")
        allergen_ids = [row[0] for row in cursor.fetchall()]

        for ing_id in allergen_ids:
            cursor.execute('''
                INSERT INTO allergens (user_id, ingredient_id, note)
                VALUES (?, ?, 'Аллергия')
            ''', (student_id, ing_id))

        print("⚠️ Тестовые аллергены добавлены.")

    # --- 9. ТЕСТОВЫЕ ОТЗЫВЫ ---
    cursor.execute('SELECT count(*) FROM reviews')
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM users WHERE role = 'student' LIMIT 1")
        student_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM dishes WHERE name = 'Борщ'")
        dish_id = cursor.fetchone()[0]

        if student_id and dish_id:
            reviews = [
                (student_id, dish_id, 5, 'Очень вкусный борщ!'),
                (student_id, dish_ids['Куриные котлеты'], 4, 'Нормальные котлеты, но мало соуса'),
                (student_id, dish_ids['Омлет'], 3, 'Пересоленный'),
            ]

            cursor.executemany('''
                INSERT INTO reviews (user_id, dish_id, rating, comment)
                VALUES (?, ?, ?, ?)
            ''', reviews)

            print("⭐ Тестовые отзывы добавлены.")

    # --- 10. ТЕСТОВЫЕ ЗАЯВКИ НА ЗАКУПКУ ---
    cursor.execute('SELECT count(*) FROM purchase_requests')
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM users WHERE role = 'cook' LIMIT 1")
        cook_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM ingredients WHERE name IN ('Картофель', 'Курица')")
        ingredient_rows = cursor.fetchall()

        for ing_id in [row[0] for row in ingredient_rows]:
            cursor.execute('''
                INSERT INTO purchase_requests (ingredient_id, quantity, requested_by, status)
                VALUES (?, ?, ?, 'pending')
            ''', (ing_id, 20.0, cook_id))

        print("🛒 Тестовые заявки на закупку добавлены.")

    conn.commit()
    conn.close()
    print("🌱 Все тестовые данные успешно загружены.")


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
    print(f"🚀 База данных {DB_NAME} полностью готова к работе!")
    print("\n📊 Схема содержит:")
    print("   - 3 роли пользователей (student, cook, admin)")
    print("   - 8 блюд с ингредиентами")
    print("   - Меню на 3 дня вперед")
    print("   - Заказы, платежи, отзывы")
    print("   - Заявки на закупку")