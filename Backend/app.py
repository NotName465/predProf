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
    conn.row_factory = sqlite3.Row  # Позволяет брать поля по имени
    return conn


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
    return render_template('register.html')


# --- Защищенные кабинеты ---

@app.route('/student')
def student_dashboard():
    if 'user_id' not in session: return redirect(url_for('login', next=flask_request.path))
    return render_template('student.html')


@app.route('/cook')
def cook_dashboard():
    if 'user_id' not in session: return redirect(url_for('login', next=flask_request.path))
    return render_template('cook.html')


@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session: return redirect(url_for('login', next=flask_request.path))
    return render_template('admin.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# --- Статика ---
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(frontend_dir, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(frontend_dir, 'js'), filename)

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(frontend_dir, 'assets'), filename)


# ========================
# API
# ========================

# 1. Вход в систему
@app.route('/api/login', methods=['POST'])
def api_login():
    data = flask_request.get_json()
    email = data.get('username', '').strip()  # С фронта приходит как username
    password = data.get('password')
    next_url = data.get('next_url')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['role'] = user['role']
        target = next_url if next_url else f"/{user['role']}"
        return jsonify({'status': 'success', 'redirect': target}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Неверная почта или пароль'}), 401


# 2. Регистрация
@app.route('/api/register', methods=['POST'])
def api_register():
    data = flask_request.get_json()
    email = data.get('email', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password')
    confirm = data.get('confirm_password')

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
        cur = conn.execute('INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)',
                           (username, email, hashed, 'student'))
        new_id = cur.lastrowid
        conn.commit()
    except:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ошибка БД'}), 500

    conn.close()
    session['user_id'] = new_id
    session['role'] = 'student'
    return jsonify({'status': 'success', 'redirect': '/student'}), 200


# 3. Получить список блюд (для повара)
@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    conn = get_db_connection()
    dishes = conn.execute('SELECT * FROM dishes').fetchall()
    conn.close()

    result = []
    for d in dishes:
        dish_dict = dict(d)
        # Распаковываем JSON
        try:
            dish_dict['ingredients'] = json.loads(dish_dict['ingredients'])
        except:
            dish_dict['ingredients'] = []
        try:
            dish_dict['reviews'] = json.loads(dish_dict['reviews'])
        except:
            dish_dict['reviews'] = []
        result.append(dish_dict)

    return jsonify(result), 200


# 4. Выдать питание (списать со склада)
@app.route('/api/issue_meal', methods=['POST'])
def issue_meal():
    data = flask_request.get_json()
    dish_id = data.get('dish_id')
    student_ident = str(data.get('student_identifier')).strip()

    conn = get_db_connection()

    # Проверка блюда
    dish = conn.execute('SELECT * FROM dishes WHERE id = ?', (dish_id,)).fetchone()
    if not dish:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Блюдо не найдено'}), 404

    if dish['stock_quantity'] <= 0:
        conn.close()
        return jsonify({'status': 'error', 'message': f'"{dish["name"]}" закончилось!'}), 400

    # Проверка ученика (ID, email или username)
    student = conn.execute('SELECT * FROM users WHERE id = ? OR email = ? OR username = ?',
                           (student_ident, student_ident, student_ident)).fetchone()

    if not student:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ученик не найден'}), 404

    # Списание
    try:
        conn.execute('UPDATE dishes SET stock_quantity = stock_quantity - 1 WHERE id = ?', (dish_id,))
        conn.commit()
        new_stock = dish['stock_quantity'] - 1
    except:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Ошибка записи'}), 500

    conn.close()
    return jsonify({
        'status': 'success',
        'message': f'Выдано: {dish["name"]} для {student["username"]}',
        'new_stock': new_stock
    }), 200


def redirect_to_role_page():
    role = session.get('role')
    return redirect(f"/{role}") if role else redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
