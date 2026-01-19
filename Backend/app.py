import sqlite3
import os
import json
from datetime import datetime, date, timedelta
from flask import Flask, render_template, send_from_directory, jsonify, session, redirect, url_for
from flask import request as flask_request
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

basedir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(basedir, '../frontend')
db_path = os.path.join(basedir, '../database/school_canteen.db')

app = Flask(__name__, template_folder=frontend_dir, static_folder=frontend_dir)
app.secret_key = 'super_secret_key_for_school_canteen'


def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def redirect_to_role_page():
    role = session.get('role')
    if role == 'student': return redirect('/student')
    if role == 'cook': return redirect('/cook')
    if role == 'admin': return redirect('/admin')
    return redirect('/login')


def check_subscription(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT subscription_end_date FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user and user['subscription_end_date']:
        try:
            end_date = datetime.strptime(user['subscription_end_date'], '%Y-%m-%d').date()
            return end_date >= date.today()
        except:
            return False
    return False


@app.route('/')
def index(): return render_template('index.html')


@app.route('/login')
def login():
    if 'user_id' in session: return redirect_to_role_page()
    return render_template('login.html')


@app.route('/register')
def register():
    if 'user_id' in session: return redirect_to_role_page()
    return render_template('login.html')


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


@app.route('/css/<path:filename>')
def serve_css(filename): return send_from_directory(os.path.join(frontend_dir, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename): return send_from_directory(os.path.join(frontend_dir, 'js'), filename)


@app.route('/assets/<path:filename>')
def serve_assets(filename): return send_from_directory(os.path.join(frontend_dir, 'assets'), filename)


# --- AUTH API ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = flask_request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password')
    next_url = data.get('next_url')
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ? OR username = ?', (username, username)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['role'] = user['role']
        target = next_url if next_url and next_url.startswith(f"/{user['role']}") else f"/{user['role']}"
        return jsonify({'status': 'success', 'redirect': target}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Неверный логин или пароль'}), 401


@app.route('/api/register', methods=['POST'])
def api_register():
    data = flask_request.get_json()
    email = data.get('email', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password')
    confirm = data.get('confirm_password')
    allergens = data.get('allergens', [])
    if not username or not password or not email: return jsonify(
        {'status': 'error', 'message': 'Заполните все поля'}), 400
    if password != confirm: return jsonify({'status': 'error', 'message': 'Пароли не совпадают'}), 400
    conn = get_db_connection()
    exist = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if exist:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Почта уже занята'}), 400
    hashed = generate_password_hash(password)
    try:
        cur = conn.execute('INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                           (username, email, hashed, 'student'))
        new_id = cur.lastrowid
        if allergens:
            for ingredient_id in allergens:
                conn.execute('INSERT INTO allergens (user_id, ingredient_id, note) VALUES (?, ?, ?)',
                             (new_id, ingredient_id, 'Указано при регистрации'))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500
    conn.close()
    session['user_id'] = new_id
    session['role'] = 'student'
    return jsonify({'status': 'success', 'redirect': '/student'}), 200


# --- USER API ---
@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    conn = get_db_connection()
    user = conn.execute('SELECT id, username, email, role, subscription_end_date FROM users WHERE id = ?',
                        (session['user_id'],)).fetchone()
    allergens = conn.execute(
        'SELECT i.id, i.name FROM allergens a JOIN ingredients i ON a.ingredient_id = i.id WHERE a.user_id = ?',
        (session['user_id'],)).fetchall()
    conn.close()
    if user:
        is_sub = check_subscription(session['user_id'])
        return jsonify({'status': 'success', 'user': {'username': user['username'], 'email': user['email'],
                                                      'has_active_subscription': is_sub,
                                                      'subscription_end_date': user['subscription_end_date']},
                        'allergens': [dict(row) for row in allergens]})
    return jsonify({'status': 'error'}), 404


@app.route('/api/user/allergens', methods=['POST'])
def update_allergens():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    data = flask_request.get_json()
    ids = data.get('allergen_ids', [])
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM allergens WHERE user_id = ?', (session['user_id'],))
        for i_id in ids:
            conn.execute('INSERT INTO allergens (user_id, ingredient_id) VALUES (?, ?)', (session['user_id'], i_id))
        conn.commit()
    except:
        conn.close()
        return jsonify({'status': 'error'}), 500
    conn.close()
    return jsonify({'status': 'success'})


@app.route('/api/payments/subscription', methods=['POST'])
def buy_subscription():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO payments (user_id, amount, type, status) VALUES (?, 1500, "subscription", "completed")',
            (session['user_id'],))
        new_end_date = (date.today() + timedelta(days=30)).isoformat()
        conn.execute('UPDATE users SET subscription_end_date = ? WHERE id = ?', (new_end_date, session['user_id']))
        conn.commit()
    except:
        conn.close()
        return jsonify({'status': 'error'}), 500
    conn.close()
    return jsonify({'status': 'success'})


# --- MENU & ORDERS API ---
@app.route('/api/menu/today', methods=['GET'])
def get_today_menu():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    conn = get_db_connection()
    today_str = date.today().isoformat()
    menu_items = conn.execute(
        'SELECT m.id, m.meal_type, m.dish_id, d.name as dish_name, d.description, d.image_url, d.calories, d.price, d.current_stock FROM menu m JOIN dishes d ON m.dish_id = d.id WHERE m.date = ?',
        (today_str,)).fetchall()
    result = {'breakfast': [], 'lunch': []}
    for item in menu_items:
        dish = dict(item)
        ings = conn.execute(
            'SELECT i.id, i.name FROM dish_ingredients di JOIN ingredients i ON di.ingredient_id = i.id WHERE di.dish_id = ?',
            (dish['dish_id'],)).fetchall()
        dish['ingredients'] = [dict(ing) for ing in ings]
        if dish['meal_type'] == 'breakfast':
            result['breakfast'].append(dish)
        else:
            result['lunch'].append(dish)
    conn.close()
    return jsonify(result)


@app.route('/api/orders', methods=['POST'])
def create_order():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    data = flask_request.get_json()
    menu_id = data.get('menu_id')
    conn = get_db_connection()
    menu_item = conn.execute(
        'SELECT m.*, d.name, d.current_stock, d.price FROM menu m JOIN dishes d ON m.dish_id = d.id WHERE m.id = ?',
        (menu_id,)).fetchone()
    if not menu_item or menu_item['current_stock'] <= 0:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Блюдо недоступно'}), 400
    existing = conn.execute('SELECT id FROM orders WHERE user_id = ? AND menu_id = ?',
                            (session['user_id'], menu_id)).fetchone()
    if existing:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Уже заказано'}), 400
    is_sub = check_subscription(session['user_id'])
    try:
        conn.execute('UPDATE dishes SET current_stock = current_stock - 1 WHERE id = ?', (menu_item['dish_id'],))
        cur = conn.execute(
            'INSERT INTO orders (user_id, menu_id, order_date, paid, collected) VALUES (?, ?, datetime("now", "localtime"), ?, 0)',
            (session['user_id'], menu_id, 1 if is_sub else 0))
        order_id = cur.lastrowid
        if not is_sub:
            conn.execute(
                'INSERT INTO payments (user_id, amount, type, order_id, status) VALUES (?, ?, "single", ?, "pending")',
                (session['user_id'], menu_item['price'], order_id))
        conn.commit()
    except:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ошибка сервера'}), 500
    conn.close()
    return jsonify({'status': 'success', 'message': 'Заказ создан!'})


@app.route('/api/orders/my', methods=['GET'])
def get_my_orders():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    conn = get_db_connection()
    orders = conn.execute(
        'SELECT o.id, o.order_date as date, m.meal_type, d.name as dish_name, d.price, o.paid, o.collected, d.id as dish_id FROM orders o JOIN menu m ON o.menu_id = m.id JOIN dishes d ON m.dish_id = d.id WHERE o.user_id = ? ORDER BY o.order_date DESC',
        (session['user_id'],)).fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])


# --- COOK API ---
@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    conn = get_db_connection()
    dishes = conn.execute('SELECT * FROM dishes').fetchall()
    conn.close()
    result = []
    for d in dishes:
        dish = dict(d)
        dish['stock_quantity'] = dish['current_stock']
        result.append(dish)
    return jsonify(result)


@app.route('/api/ingredients', methods=['GET'])
def get_ingredients():
    conn = get_db_connection()
    ings = conn.execute('SELECT * FROM ingredients').fetchall()
    conn.close()
    return jsonify([dict(i) for i in ings])


@app.route('/api/issue_meal', methods=['POST'])
def issue_meal():
    if session.get('role') not in ['cook', 'admin']: return jsonify({'status': 'error'}), 403
    data = flask_request.get_json()
    dish_id = data.get('dish_id')
    student_ident = str(data.get('student_identifier')).strip()
    conn = get_db_connection()
    dish = conn.execute('SELECT * FROM dishes WHERE id = ?', (dish_id,)).fetchone()
    if not dish or dish['current_stock'] <= 0:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Нет в наличии'}), 400
    student = conn.execute('SELECT id, username FROM users WHERE id = ? OR email = ? OR username = ?',
                           (student_ident, student_ident, student_ident)).fetchone()
    if not student:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ученик не найден'}), 404
    try:
        conn.execute('UPDATE dishes SET current_stock = current_stock - 1 WHERE id = ?', (dish_id,))
        today = date.today().isoformat()
        menu = conn.execute('SELECT id FROM menu WHERE date = ? AND dish_id = ?', (today, dish_id)).fetchone()
        if menu:
            menu_id = menu['id']
        else:
            cur = conn.execute("INSERT INTO menu (date, meal_type, dish_id) VALUES (?, 'lunch', ?)", (today, dish_id))
            menu_id = cur.lastrowid
        conn.execute(
            'INSERT INTO orders (user_id, menu_id, order_date, paid, collected) VALUES (?, ?, datetime("now", "localtime"), 1, 1)',
            (student['id'], menu_id))
        conn.commit()
        new_stock = dish['current_stock'] - 1
    except:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500
    conn.close()
    return jsonify(
        {'status': 'success', 'message': f'Выдано: {dish["name"]} для {student["username"]}', 'new_stock': new_stock})


@app.route('/api/add_dish', methods=['POST'])
def add_dish():
    if session.get('role') not in ['cook', 'admin']: return jsonify({'status': 'error'}), 403
    name = flask_request.form.get('name')
    stock = flask_request.form.get('stock')
    cals = flask_request.form.get('calories')
    file = flask_request.files.get('image')
    img_url = ''
    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join(frontend_dir, 'assets', filename))
        img_url = f'/assets/{filename}'
    conn = get_db_connection()
    conn.execute('INSERT INTO dishes (name, current_stock, calories, image_url) VALUES (?, ?, ?, ?)',
                 (name, stock, cals, img_url))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})


@app.route('/api/purchase_requests', methods=['GET'])
def get_purchase_requests():
    if session.get('role') not in ['cook', 'admin']: return jsonify({'status': 'error'}), 403
    conn = get_db_connection()
    requests = conn.execute('''
        SELECT pr.id, i.name as ingredient_name, pr.quantity, i.unit, pr.status, pr.request_date, u.username as requester
        FROM purchase_requests pr
        JOIN ingredients i ON pr.ingredient_id = i.id
        JOIN users u ON pr.requested_by = u.id
        ORDER BY pr.request_date DESC
        LIMIT 50
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in requests]), 200


@app.route('/api/purchase_requests', methods=['POST'])
def create_purchase_request():
    if session.get('role') != 'cook': return jsonify({'status': 'error'}), 403
    data = flask_request.get_json()
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO purchase_requests (ingredient_id, quantity, requested_by, status) VALUES (?, ?, ?, "pending")',
        (data.get('ingredient_id'), data.get('quantity'), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'}), 200


@app.route('/api/stats/cook', methods=['GET'])
def get_cook_stats():
    if session.get('role') not in ['cook', 'admin']: return jsonify({'status': 'error'}), 403
    conn = get_db_connection()

    def count(m_type, is_issued):
        cond = "collected=1" if is_issued else "paid=1"
        return conn.execute(
            f"SELECT COUNT(o.id) as c FROM orders o JOIN menu m ON o.menu_id=m.id WHERE o.{cond} AND date(o.order_date)=date('now', 'localtime') AND m.meal_type=?",
            (m_type,)).fetchone()['c']

    stats = {
        'breakfast': {'issued': count('breakfast', True), 'sold': count('breakfast', False)},
        'lunch': {'issued': count('lunch', True), 'sold': count('lunch', False)}
    }
    top = conn.execute(
        "SELECT d.name, COUNT(o.id) as count FROM orders o JOIN menu m ON o.menu_id=m.id JOIN dishes d ON m.dish_id=d.id WHERE date(o.order_date)=date('now', 'localtime') GROUP BY d.name ORDER BY count DESC").fetchall()
    conn.close()
    return jsonify({'breakfast': stats['breakfast'], 'lunch': stats['lunch'],
                    'breakdown': [{'name': r['name'], 'count': r['count']} for r in top]}), 200


@app.route('/api/reviews', methods=['POST'])
def add_review():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    data = flask_request.get_json()
    conn = get_db_connection()
    conn.execute('INSERT INTO reviews (user_id, dish_id, rating, comment) VALUES (?, ?, ?, ?)',
                 (session['user_id'], data.get('dish_id'), data.get('rating'), data.get('comment')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Отзыв добавлен'}), 200


# ========================
# ADMIN API (НОВОЕ)
# ========================

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    if session.get('role') != 'admin': return jsonify({'status': 'error'}), 403
    conn = get_db_connection()

    # Посещаемость (всего заказов за сегодня)
    attendance = \
    conn.execute("SELECT COUNT(*) as c FROM orders WHERE date(order_date)=date('now', 'localtime')").fetchone()['c']

    # Выручка за сегодня (из таблицы payments)
    revenue_today = conn.execute(
        "SELECT SUM(amount) as s FROM payments WHERE status='completed' AND date(payment_date)=date('now', 'localtime')").fetchone()[
                        's'] or 0

    # Всего выдано порций за все время (исторические данные)
    total_issued = conn.execute("SELECT COUNT(*) as c FROM orders WHERE collected=1").fetchone()['c']

    conn.close()
    return jsonify({
        'attendance_today': attendance,
        'revenue_today': revenue_today,
        'total_issued': total_issued
    }), 200


@app.route('/api/purchase_requests/<int:req_id>', methods=['PUT'])
def update_purchase_request(req_id):
    if session.get('role') != 'admin': return jsonify({'status': 'error'}), 403
    data = flask_request.get_json()
    status = data.get('status')

    if status not in ['approved', 'rejected']: return jsonify({'status': 'error'}), 400

    conn = get_db_connection()
    try:
        # Обновляем статус заявки
        conn.execute('''
            UPDATE purchase_requests 
            SET status = ?, approved_by = ?, approved_date = datetime('now', 'localtime') 
            WHERE id = ?
        ''', (status, session['user_id'], req_id))

        # Если одобрено - увеличиваем кол-во ингредиентов на складе
        if status == 'approved':
            req = conn.execute('SELECT ingredient_id, quantity FROM purchase_requests WHERE id = ?',
                               (req_id,)).fetchone()
            if req:
                conn.execute('UPDATE ingredients SET current_quantity = current_quantity + ? WHERE id = ?',
                             (req['quantity'], req['ingredient_id']))

        conn.commit()
    except Exception as e:
        conn.close()
        print(f"Error updating request: {e}")
        return jsonify({'status': 'error'}), 500

    conn.close()
    return jsonify({'status': 'success'}), 200


@app.route('/api/admin/reports', methods=['GET'])
def get_reports():
    if session.get('role') != 'admin': return jsonify({'status': 'error'}), 403
    conn = get_db_connection()

    # Отчет: продажи по дням (последние 7 дней)
    reports = conn.execute('''
        SELECT date(payment_date) as date, SUM(amount) as revenue, COUNT(*) as transactions
        FROM payments
        WHERE status='completed'
        GROUP BY date(payment_date)
        ORDER BY date DESC
        LIMIT 7
    ''').fetchall()

    conn.close()
    return jsonify([dict(r) for r in reports]), 200


if __name__ == '__main__':
    app.run(debug=True)
