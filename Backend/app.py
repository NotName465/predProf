import sqlite3
import os
from flask import Flask, render_template, send_from_directory, jsonify, session, redirect, url_for
from flask import request as flask_request
from werkzeug.security import check_password_hash, generate_password_hash
import json
# 1. Настройка путей
# Мы находимся в backend/app.py
basedir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(basedir, '../frontend')
# Путь к базе данных (она лежит в папке database)
db_path = os.path.join(basedir, '../database/school_canteen.db')

app = Flask(__name__,
            template_folder=frontend_dir,
            static_folder=frontend_dir)

app.secret_key = 'super_secret_key_for_school_canteen'


# --- Функция подключения к БД ---
def get_db_connection():
    conn = sqlite3.connect(db_path)
    # Позволяет обращаться к колонкам по имени (row['email']), а не по индексу
    conn.row_factory = sqlite3.Row
    return conn


# ========================
# Маршруты страниц (HTML)
# ========================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    # Если пользователь уже вошел (есть user_id в сессии), кидаем в ЛК
    if 'user_id' in session:
        return redirect_to_role_page()
    return render_template('login.html')


@app.route('/register')
def register():
    if 'user_id' in session:
        return redirect_to_role_page()
    return render_template('register.html')


# --- Защищенные страницы ---

@app.route('/student')
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login', next=flask_request.path))
    return render_template('student.html')


@app.route('/cook')
def cook_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login', next=flask_request.path))
    return render_template('cook.html')


@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login', next=flask_request.path))
    return render_template('admin.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# --- Статика (CSS/JS) ---
@app.route('/css/<path:filename>')
def serve_css(filename): return send_from_directory(os.path.join(frontend_dir, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename): return send_from_directory(os.path.join(frontend_dir, 'js'), filename)


# ========================
# API (Логика работы с БД)
# ========================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = flask_request.get_json()

    # В поле username с фронта может прийти email (по заданию логин = почта)
    email = data.get('username', '').strip()
    password = data.get('password')
    next_url = data.get('next_url')

    conn = get_db_connection()
    # Ищем пользователя по Email
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    # Если юзер найден И хеш пароля совпадает
    if user and check_password_hash(user['password_hash'], password):
        # Сохраняем ID и роль в сессию
        session['user_id'] = user['id']
        session['role'] = user['role']

        # Определяем куда перенаправить
        target = next_url if next_url else f"/{user['role']}"

        return jsonify({'status': 'success', 'redirect': target}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Неверная почта или пароль'}), 401


@app.route('/api/register', methods=['POST'])
def api_register():
    data = flask_request.get_json()

    email = data.get('email', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    # Простая валидация
    if not username or not password or not email:
        return jsonify({'status': 'error', 'message': 'Заполните все поля'}), 400

    if password != confirm_password:
        return jsonify({'status': 'error', 'message': 'Пароли не совпадают'}), 400

    conn = get_db_connection()

    # Проверяем, не занята ли почта
    existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

    if existing_user:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Пользователь с такой почтой уже существует'}), 400

    # Хешируем пароль перед записью в БД
    hashed_password = generate_password_hash(password)

    try:
        # Добавляем нового ученика (роль student по умолчанию)
        cursor = conn.execute('''
            INSERT INTO users (username, email, password_hash, role, subscription_days)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, hashed_password, 'student', 0))

        new_user_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        print(f"Ошибка БД: {e}")
        return jsonify({'status': 'error', 'message': 'Ошибка при сохранении в базу'}), 500

    conn.close()

    # Автоматический вход
    session['user_id'] = new_user_id
    session['role'] = 'student'

    return jsonify({'status': 'success', 'redirect': '/student'}), 200

# API для повара (ПЕРЕПИСАТЬ!)
@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    conn = get_db_connection()
    dishes = conn.execute('SELECT * FROM dishes').fetchall()
    conn.close()

    # SQLite возвращает строки, а нам нужно распаковать JSON-поля (ингредиенты)
    result = []
    for dish in dishes:
        d = dict(dish)  # Превращаем строку БД в словарь
        # Распаковываем JSON строку обратно в список ['Лук', 'Морковь']
        try:
            d['ingredients'] = json.loads(d['ingredients'])
        except:
            d['ingredients'] = []  # Если ошибка или пусто

        result.append(d)

    return jsonify(result), 200

    return jsonify(dishes_list), 200
def redirect_to_role_page():
    """Помощник: перенаправляет на страницу роли"""
    role = session.get('role')
    if role:
        return redirect(f"/{role}")
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
