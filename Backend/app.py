import sqlite3
import os
import json
from datetime import datetime, date
from flask import Flask, render_template, send_from_directory, jsonify, session, redirect, url_for
from flask import request as flask_request
from werkzeug.security import check_password_hash, generate_password_hash

# --- Настройка путей ---
basedir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(basedir, '../Frontend')
db_path = os.path.join(basedir, '../database/school_canteen.db')

app = Flask(__name__,
            template_folder=frontend_dir,
            static_folder=frontend_dir)

app.secret_key = 'super_secret_key_for_school_canteen'


def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# --- Вспомогательная функция перенаправления ---
def redirect_to_role_page():
    role = session.get('role')
    if role == 'student': return redirect('/student')
    if role == 'cook': return redirect('/cook')
    if role == 'admin': return redirect('/admin')
    return redirect('/login')


def check_subscription(user_id):
    """Проверяет активную подписку пользователя"""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT subscription_end_date FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    conn.close()

    if user and user['subscription_end_date']:
        try:
            end_date = datetime.strptime(user['subscription_end_date'], '%Y-%m-%d').date()
            return end_date >= date.today()
        except:
            return False
    return False


# ========================
# МАРШРУТЫ СТРАНИЦ
# ========================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect_to_role_page()
    return render_template('login.html')


@app.route('/register')
def register():
    if 'user_id' in session:
        return redirect_to_role_page()
    return render_template('login.html')


# --- Защищенные кабинеты (RBAC) ---

@app.route('/student')
def student_dashboard():
    if 'user_id' not in session: return redirect(url_for('login', next=flask_request.path))
    if session.get('role') != 'student': return redirect_to_role_page()
    return render_template('student.html')


@app.route('/cook')
def cook_dashboard():
    if 'user_id' not in session: return redirect(url_for('login', next=flask_request.path))
    if session.get('role') != 'cook': return redirect_to_role_page()
    return render_template('cook.html')


@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session: return redirect(url_for('login', next=flask_request.path))
    if session.get('role') != 'admin': return redirect_to_role_page()
    return render_template('admin.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# --- Статика ---
@app.route('/css/<path:filename>')
def serve_css(filename): return send_from_directory(os.path.join(frontend_dir, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename): return send_from_directory(os.path.join(frontend_dir, 'js'), filename)


@app.route('/assets/<path:filename>')
def serve_assets(filename): return send_from_directory(os.path.join(frontend_dir, 'assets'), filename)


# ========================
# API ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# ========================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = flask_request.get_json()
    email = data.get('username', '').strip()
    password = data.get('password')
    next_url = data.get('next_url')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['role'] = user['role']

        if next_url and next_url.startswith(f"/{user['role']}"):
            target = next_url
        else:
            target = f"/{user['role']}"

        return jsonify({'status': 'success', 'redirect': target}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Неверная почта или пароль'}), 401


@app.route('/api/register', methods=['POST'])
def api_register():
    data = flask_request.get_json()
    email = data.get('email', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password')
    confirm = data.get('confirm_password')
    allergens = data.get('allergens', [])  # Список ID ингредиентов

    if not username or not password or not email:
        return jsonify({'status': 'error', 'message': 'Заполните все поля'}), 400
    if password != confirm:
        return jsonify({'status': 'error', 'message': 'Пароли не совпадают'}), 400

    conn = get_db_connection()
    exist = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

    if exist:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Почта уже занята'}), 400

    hashed = generate_password_hash(password)

    try:
        cur = conn.execute('''
            INSERT INTO users (username, email, password_hash, role) 
            VALUES (?, ?, ?, ?)
        ''', (username, email, hashed, 'student'))
        new_id = cur.lastrowid

        if allergens:
            for ingredient_id in allergens:
                conn.execute('''
                    INSERT INTO allergens (user_id, ingredient_id, note)
                    VALUES (?, ?, 'Указано при регистрации')
                ''', (new_id, ingredient_id))

        conn.commit()
    except Exception as e:
        conn.close()
        print(f"Ошибка регистрации: {e}")
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500

    conn.close()
    session['user_id'] = new_id
    session['role'] = 'student'
    return jsonify({'status': 'success', 'redirect': '/student'}), 200


@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """Получение профиля пользователя с информацией о подписке и аллергенах"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Не авторизован'}), 401

    conn = get_db_connection()
    user = conn.execute('''
        SELECT id, username, email, role, subscription_end_date 
        FROM users WHERE id = ?
    ''', (session['user_id'],)).fetchone()

    # Получаем аллергены пользователя
    allergens = conn.execute('''
        SELECT i.id, i.name 
        FROM allergens a
        JOIN ingredients i ON a.ingredient_id = i.id
        WHERE a.user_id = ?
    ''', (session['user_id'],)).fetchall()

    conn.close()

    if user:
        has_active_subscription = check_subscription(session['user_id'])
        return jsonify({
            'status': 'success',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'subscription_end_date': user['subscription_end_date'],
                'has_active_subscription': has_active_subscription
            },
            'allergens': [{'id': a['id'], 'name': a['name']} for a in allergens]
        }), 200

    return jsonify({'status': 'error', 'message': 'Пользователь не найден'}), 404


# ========================
# API ДЛЯ МЕНЮ (для студента)
# ========================

@app.route('/api/menu/today', methods=['GET'])
def get_today_menu():
    """Получение меню на сегодня"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Не авторизован'}), 401

    conn = get_db_connection()

    # Получаем меню на сегодня
    menu = conn.execute('''
        SELECT m.*, d.name as dish_name, d.description, d.image_url, 
               d.calories, d.price, d.current_stock
        FROM menu m
        JOIN dishes d ON m.dish_id = d.id
        WHERE m.date = date('now')
        ORDER BY 
            CASE m.meal_type 
                WHEN 'breakfast' THEN 1
                WHEN 'lunch' THEN 2
            END,
            d.name
    ''').fetchall()

    if not menu:
        conn.close()
        return jsonify({
            'date': date.today().isoformat(),
            'breakfast': [],
            'lunch': []
        }), 200

    # Получаем ингредиенты для всех блюд в меню
    dish_ids = [item['dish_id'] for item in menu]
    placeholders = ','.join('?' for _ in dish_ids)

    ingredients_data = conn.execute(f'''
        SELECT di.dish_id, i.id, i.name
        FROM dish_ingredients di
        JOIN ingredients i ON di.ingredient_id = i.id
        WHERE di.dish_id IN ({placeholders})
    ''', dish_ids).fetchall()

    # Группируем ингредиенты по dish_id
    ingredients_by_dish = {}
    for ing in ingredients_data:
        dish_id = ing['dish_id']
        if dish_id not in ingredients_by_dish:
            ingredients_by_dish[dish_id] = []
        ingredients_by_dish[dish_id].append({
            'id': ing['id'],
            'name': ing['name']
        })

    # Группируем меню по типам приема пищи
    breakfast = []
    lunch = []

    for item in menu:
        menu_item = dict(item)
        dish_id = item['dish_id']

        # Добавляем ингредиенты к блюду
        menu_item['ingredients'] = ingredients_by_dish.get(dish_id, [])

        if item['meal_type'] == 'breakfast':
            breakfast.append(menu_item)
        else:
            lunch.append(menu_item)

    conn.close()

    return jsonify({
        'date': date.today().isoformat(),
        'breakfast': breakfast,
        'lunch': lunch
    }), 200


@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    """Получение всех блюд с ингредиентами"""
    conn = get_db_connection()

    dishes = conn.execute('''
        SELECT d.*, 
               GROUP_CONCAT(DISTINCT i.name) as ingredient_names
        FROM dishes d
        LEFT JOIN dish_ingredients di ON d.id = di.dish_id
        LEFT JOIN ingredients i ON di.ingredient_id = i.id
        GROUP BY d.id
        ORDER BY d.name
    ''').fetchall()

    conn.close()
    result = []
    for d in dishes:
        dish = dict(d)
        dish['ingredients'] = d['ingredient_names'].split(',') if d['ingredient_names'] else []
        dish['reviews'] = []  # Для совместимости
        dish['stock_quantity'] = dish.get('current_stock', 0)  # Для совместимости
        result.append(dish)
    return jsonify(result), 200


# ========================
# API ДЛЯ ЗАКАЗОВ (для студента)
# ========================

@app.route('/api/orders/my', methods=['GET'])
def get_my_orders():
    """Получение заказов текущего пользователя"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Не авторизован'}), 401

    conn = get_db_connection()

    orders = conn.execute('''
        SELECT o.*, m.date, m.meal_type, d.name as dish_name, d.image_url, d.price
        FROM orders o
        JOIN menu m ON o.menu_id = m.id
        JOIN dishes d ON m.dish_id = d.id
        WHERE o.user_id = ?
        ORDER BY o.order_date DESC
        LIMIT 20
    ''', (session['user_id'],)).fetchall()

    result = []
    for order in orders:
        order_dict = dict(order)
        # Преобразуем даты в строки для JSON
        order_dict['date'] = order['date']
        order_dict['order_date'] = order['order_date']
        result.append(order_dict)

    conn.close()
    return jsonify(result), 200


@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создание нового заказа"""
    if 'user_id' not in session or session.get('role') != 'student':
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403

    data = flask_request.get_json()
    menu_id = data.get('menu_id')

    if not menu_id:
        return jsonify({'status': 'error', 'message': 'Не указано меню'}), 400

    conn = get_db_connection()

    # Проверяем существование меню
    menu_item = conn.execute('''
        SELECT m.*, d.name as dish_name, d.current_stock, d.price
        FROM menu m
        JOIN dishes d ON m.dish_id = d.id
        WHERE m.id = ?
    ''', (menu_id,)).fetchone()

    if not menu_item:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Позиция меню не найдена'}), 404

    # Проверяем остатки
    if menu_item['current_stock'] <= 0:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Блюдо закончилось'}), 400

    # Проверяем, не заказал ли уже ученик этот прием пищи сегодня
    existing_order = conn.execute('''
        SELECT o.id FROM orders o
        JOIN menu m ON o.menu_id = m.id
        WHERE o.user_id = ? AND m.date = ? AND m.meal_type = ?
    ''', (session['user_id'], menu_item['date'], menu_item['meal_type'])).fetchone()

    if existing_order:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Вы уже заказали этот прием пищи сегодня'}), 400

    # Проверяем подписку
    has_subscription = check_subscription(session['user_id'])
    paid = has_subscription  # Если есть подписка - автоматически оплачено

    try:
        # Создаем заказ
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (user_id, menu_id, paid, collected)
            VALUES (?, ?, ?, 0)
        ''', (session['user_id'], menu_id, 1 if paid else 0))
        order_id = cursor.lastrowid

        # Уменьшаем остаток блюда
        conn.execute('''
            UPDATE dishes SET current_stock = current_stock - 1 WHERE id = ?
        ''', (menu_item['dish_id'],))

        # Если нет подписки, создаем запись о платеже
        if not paid:
            cursor.execute('''
                INSERT INTO payments (user_id, amount, type, order_id, status)
                VALUES (?, ?, 'single', ?, 'pending')
            ''', (session['user_id'], menu_item['price'], order_id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Ошибка создания заказа: {e}")
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500

    conn.close()
    return jsonify({
        'status': 'success',
        'message': f'Заказ создан: {menu_item["dish_name"]}',
        'order_id': order_id,
        'paid': paid
    }), 200


# ========================
# API ДЛЯ ПЛАТЕЖЕЙ И ПОДПИСОК
# ========================

@app.route('/api/payments/subscription', methods=['POST'])
def buy_subscription():
    """Покупка подписки"""
    if 'user_id' not in session or session.get('role') != 'student':
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403

    data = flask_request.get_json()
    days = data.get('days', 30)
    amount = data.get('amount', 1500.0)

    conn = get_db_connection()

    try:
        # Создаем платеж
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (user_id, amount, type, status)
            VALUES (?, ?, 'subscription', 'completed')
        ''', (session['user_id'], amount))

        # Обновляем дату окончания подписки
        from datetime import datetime, timedelta
        end_date = (datetime.now() + timedelta(days=days)).date().isoformat()

        conn.execute('''
            UPDATE users 
            SET subscription_end_date = ?
            WHERE id = ?
        ''', (end_date, session['user_id']))

        conn.commit()

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Ошибка покупки подписки: {e}")
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500

    conn.close()
    return jsonify({
        'status': 'success',
        'message': f'Подписка оформлена на {days} дней',
        'subscription_end_date': end_date
    }), 200


# ========================
# API ДЛЯ ОТЗЫВОВ
# ========================

@app.route('/api/reviews', methods=['POST'])
def add_review():
    """Добавление отзыва"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Не авторизован'}), 401

    data = flask_request.get_json()
    dish_id = data.get('dish_id')
    rating = data.get('rating')
    comment = data.get('comment', '').strip()

    if not dish_id or not rating or not (1 <= rating <= 5):
        return jsonify({'status': 'error', 'message': 'Некорректные данные'}), 400

    conn = get_db_connection()

    # Проверяем, есть ли у пользователя заказы этого блюда
    has_ordered = conn.execute('''
        SELECT COUNT(*) as count
        FROM orders o
        JOIN menu m ON o.menu_id = m.id
        WHERE o.user_id = ? AND m.dish_id = ?
    ''', (session['user_id'], dish_id)).fetchone()

    if has_ordered['count'] == 0:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Вы не заказывали это блюдо'}), 400

    try:
        conn.execute('''
            INSERT INTO reviews (user_id, dish_id, rating, comment)
            VALUES (?, ?, ?, ?)
        ''', (session['user_id'], dish_id, rating, comment))
        conn.commit()

    except Exception as e:
        conn.close()
        print(f"Ошибка добавления отзыва: {e}")
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500

    conn.close()
    return jsonify({'status': 'success', 'message': 'Отзыв добавлен'}), 200


# ========================
# API ДЛЯ ПОВАРА (сохранено для обратной совместимости)
# ========================

@app.route('/api/issue_meal', methods=['POST'])
def issue_meal():
    """Выдача еды (для повара)"""
    if session.get('role') not in ['cook', 'admin']:
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403

    data = flask_request.get_json()
    dish_id = data.get('dish_id')
    student_ident = str(data.get('student_identifier')).strip()

    conn = get_db_connection()

    dish = conn.execute('SELECT * FROM dishes WHERE id = ?', (dish_id,)).fetchone()

    if not dish:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Блюдо не найдено'}), 404

    if dish['current_stock'] <= 0:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Блюдо закончилось'}), 400

    student = conn.execute('SELECT * FROM users WHERE (id = ? OR email = ? OR username = ?) AND role = "student"',
                           (student_ident, student_ident, student_ident)).fetchone()
    if not student:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ученик не найден'}), 404

    try:
        conn.execute('UPDATE dishes SET current_stock = current_stock - 1 WHERE id = ?', (dish_id,))
        conn.commit()
        new_stock = dish['current_stock'] - 1
    except Exception as e:
        conn.close()
        print(f"Ошибка выдачи еды: {e}")
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500

    conn.close()
    return jsonify({'status': 'success', 'message': f'Выдано: {dish["name"]}', 'new_stock': new_stock}), 200


# ========================
# API ДЛЯ АЛЛЕРГЕНОВ
# ========================

@app.route('/api/ingredients', methods=['GET'])
def get_ingredients():
    """Получение списка всех ингредиентов (для выбора аллергенов)"""
    conn = get_db_connection()

    ingredients = conn.execute('''
        SELECT id, name, unit FROM ingredients 
        ORDER BY name
    ''').fetchall()

    conn.close()
    return jsonify([dict(ing) for ing in ingredients]), 200


@app.route('/api/user/allergens', methods=['GET'])
def get_user_allergens():
    """Получение аллергенов текущего пользователя"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Не авторизован'}), 401

    conn = get_db_connection()

    allergens = conn.execute('''
        SELECT a.*, i.name as ingredient_name 
        FROM allergens a
        JOIN ingredients i ON a.ingredient_id = i.id
        WHERE a.user_id = ?
    ''', (session['user_id'],)).fetchall()

    conn.close()
    return jsonify([dict(a) for a in allergens]), 200


@app.route('/api/user/allergens', methods=['POST'])
def update_user_allergens():
    """Обновление аллергенов пользователя"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Не авторизован'}), 401

    data = flask_request.get_json()
    allergen_ids = data.get('allergen_ids', [])

    conn = get_db_connection()

    try:
        # Удаляем старые аллергены
        conn.execute('DELETE FROM allergens WHERE user_id = ?', (session['user_id'],))

        # Добавляем новые
        for ingredient_id in allergen_ids:
            conn.execute('''
                INSERT INTO allergens (user_id, ingredient_id, note)
                VALUES (?, ?, 'Указано пользователем')
            ''', (session['user_id'], ingredient_id))

        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Аллергены обновлены'}), 200

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Ошибка обновления аллергенов: {e}")
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500
# ========================
# ТЕСТОВЫЕ ЭНДПОИНТЫ ДЛЯ ОТЛАДКИ
# ========================

@app.route('/api/debug/users', methods=['GET'])
def debug_users():
    """Просмотр всех пользователей (для отладки)"""
    if session.get('role') != 'admin':
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403

    conn = get_db_connection()
    users = conn.execute('SELECT id, username, email, role FROM users').fetchall()
    conn.close()
    return jsonify([dict(user) for user in users]), 200


@app.route('/api/debug/tables', methods=['GET'])
def debug_tables():
    """Информация о таблицах (для отладки)"""
    conn = get_db_connection()

    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

    result = {}
    for table in tables:
        count = conn.execute(f'SELECT COUNT(*) as cnt FROM {table["name"]}').fetchone()['cnt']
        result[table['name']] = count

    conn.close()
    return jsonify(result), 200


if __name__ == '__main__':
    print("=" * 60)
    print("ШКОЛЬНАЯ СТОЛОВАЯ - Flask сервер")
    print("=" * 60)
    print(f"База данных: {db_path}")
    print(f"Существует: {os.path.exists(db_path)}")
    print("=" * 60)
    print("Сервер запущен: http://localhost:5000")
    print("=" * 60)
    print("Доступные API эндпоинты:")
    print("  Для студента:")
    print("    GET  /api/user/profile - профиль пользователя")
    print("    GET  /api/menu/today - меню на сегодня")
    print("    GET  /api/orders/my - мои заказы")
    print("    POST /api/orders - создать заказ")
    print("    POST /api/payments/subscription - купить подписку")
    print("    POST /api/reviews - оставить отзыв")
    print("  Для повара:")
    print("    POST /api/issue_meal - выдать питание")
    print("  Общие:")
    print("    GET  /api/dishes - все блюда")
    print("=" * 60)

    app.run(debug=True, port=5000)