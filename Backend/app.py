import sqlite3
import os
import json
from flask import Flask, render_template, send_from_directory, jsonify, session, redirect, url_for
from flask import request as flask_request
from werkzeug.security import check_password_hash, generate_password_hash

# --- Настройка путей ---
basedir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(basedir, '../frontend')
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
    return render_template('login.html')  # Используем тот же шаблон, там есть переключатель


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
# API
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

        # Если пользователь пытался попасть на конкретную страницу (next_url),
        # мы проверяем, имеет ли он право туда идти.
        # Для простоты: если роль совпадает с началом URL или next_url пуст -> переходим
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
    allergens = data.get('allergens', [])  # Список аллергенов

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
    allergens_json = json.dumps(allergens)

    try:
        cur = conn.execute('''
            INSERT INTO users (username, email, password_hash, role, allergens) 
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, hashed, 'student', allergens_json))
        new_id = cur.lastrowid
        conn.commit()
    except:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500

    conn.close()
    session['user_id'] = new_id
    session['role'] = 'student'
    return jsonify({'status': 'success', 'redirect': '/student'}), 200


@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    conn = get_db_connection()
    dishes = conn.execute('SELECT * FROM dishes').fetchall()
    conn.close()
    result = []
    for d in dishes:
        dish = dict(d)
        try:
            dish['ingredients'] = json.loads(dish['ingredients'])
        except:
            dish['ingredients'] = []
        try:
            dish['reviews'] = json.loads(dish['reviews'])
        except:
            dish['reviews'] = []
        result.append(dish)
    return jsonify(result), 200


@app.route('/api/issue_meal', methods=['POST'])
def issue_meal():
    # Только повар (или админ) может выдавать еду!
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
    if dish['stock_quantity'] <= 0:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Блюдо закончилось'}), 400

    student = conn.execute('SELECT * FROM users WHERE id = ? OR email = ? OR username = ?',
                           (student_ident, student_ident, student_ident)).fetchone()
    if not student:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ученик не найден'}), 404

    try:
        conn.execute('UPDATE dishes SET stock_quantity = stock_quantity - 1 WHERE id = ?', (dish_id,))
        conn.commit()
        new_stock = dish['stock_quantity'] - 1
    except:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500

    conn.close()
    return jsonify({'status': 'success', 'message': f'Выдано: {dish["name"]}', 'new_stock': new_stock}), 200


if __name__ == '__main__':
    app.run(debug=True)