
from flask import Flask, render_template, send_from_directory, jsonify, session, redirect, url_for
from flask import request as flask_request
import os

# 1. НАСТРОЙКА ПУТЕЙ
# Указываем Flask'у, что HTML и CSS лежат в папке ../frontend
basedir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(basedir, '../frontend')

import os
from flask import Flask, render_template, send_from_directory, jsonify, request


basedir = os.path.dirname(os.path.abspath(__file__))
# Путь к папке frontend
frontend_dir = os.path.join(basedir, '../Frontend')

# template_folder — где HTML
# static_folder — где CSS и JS
app = Flask(__name__,
            template_folder=frontend_dir,
            static_folder=frontend_dir)


# Секретный ключ обязателен для работы сессий (кук)
app.secret_key = 'super_secret_key_for_school_canteen'

# ==========================================
# ЗАГЛУШКА БАЗЫ ДАННЫХ (В ОПЕРАТИВНОЙ ПАМЯТИ)
# ==========================================
# Здесь хранятся пользователи. При перезапуске сервера новые удалятся.
users_db = {
    'student': {
        'password': '1234',
        'role': 'student',
        'redirect': '/student',
        'full_name': 'Тестовый Ученик'
    },
    'cook': {
        'password': '1234',
        'role': 'cook',
        'redirect': '/cook',
        'full_name': 'Тестовый Повар'
    },
    'admin': {
        'password': '1234',
        'role': 'admin',
        'redirect': '/admin',
        'full_name': 'Администратор'
    }
}




@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    # Если уже авторизован - отправляем внутрь
    if 'user' in session:
        return redirect_to_role_page()
    return render_template('login.html')


@app.route('/register')
def register():
    # Если уже авторизован - на регистрации делать нечего
    if 'user' in session:
        return redirect_to_role_page()
    return render_template('register.html')


# --- ЗАЩИЩЕННЫЕ СТРАНИЦЫ ---

@app.route('/student')
def student_dashboard():
    if 'user' not in session:
        # Если не вошел - кидаем на логин, но запоминаем, куда хотел (next=...)
        return redirect(url_for('login', next=flask_request.path))
    return render_template('student.html')


@app.route('/cook')
def cook_dashboard():
    if 'user' not in session:
        return redirect(url_for('login', next=flask_request.path))
    return render_template('cook.html')


@app.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('login', next=flask_request.path))
    return render_template('admin.html')


@app.route('/logout')
def logout():
    session.clear()  # Удаляем сессию
    return redirect('/login')


@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/student')
def student_dashboard():
    # Тут будет проверка на права(скоро)
    return render_template('student.html')

@app.route('/cook')
def cook_dashboard():
    # Тут будет проверка на права(скоро)
    return render_template('cook.html')

@app.route('/admin')
def admin_dashboard():
    # Тут будет проверка на права(скоро)
    return render_template('admin.html')

#Подтягиваем директории где лежат CSS и JS
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(frontend_dir, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(frontend_dir, 'js'), filename)


@app.route('/api/login', methods=['POST'])
def api_login():
    data = flask_request.get_json()

    # Считываем данные и сразу убираем пробелы (strip)
    username = data.get('username', '').strip()
    password = data.get('password')
    next_url = data.get('next_url')  # Ссылка, куда юзер хотел попасть

    print(f"Попытка входа: '{username}' с паролем '{password}'")

    user = users_db.get(username)

    # Проверка пароля (пока просто сравнение строк)
    if user and user['password'] == password:
        # Успех: создаем сессию
        session['user'] = username
        session['role'] = user['role']

        # Определяем, куда перенаправить:
        # 1. Если был next_url (юзер нажал "Повар" -> Логин) -> идем туда
        # 2. Если нет -> идем на стандартную страницу роли
        target = next_url if next_url else user['redirect']

        return jsonify({
            'status': 'success',
            'message': 'Вход выполнен!',
            'redirect': target
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'message': 'Неверный логин или пароль'
        }), 401


@app.route('/api/register', methods=['POST'])
def api_register():
    data = flask_request.get_json()

    # Считываем и чистим данные
    email = data.get('email', '').strip()
    username = data.get('username', '').strip()
    full_name = data.get('full_name', '').strip()
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    print(f"Попытка регистрации: {username} ({email})")

    # 1. Проверка обязательных полей
    if not username or not password or not email:
        return jsonify({'status': 'error', 'message': 'Заполните все поля'}), 400

    # 2. Проверка: занят ли логин?
    if username in users_db:
        return jsonify({'status': 'error', 'message': 'Логин уже занят'}), 400

    # 3. Проверка совпадения паролей
    if password != confirm_password:
        return jsonify({'status': 'error', 'message': 'Пароли не совпадают'}), 400

    # 4. "Сохранение" в базу
    users_db[username] = {
        'password': password,
        'role': 'student',  # Новые пользователи по умолчанию - студенты
        'redirect': '/student',
        'email': email,
        'full_name': full_name
    }

    # 5. Автоматический вход после регистрации
    session['user'] = username
    session['role'] = 'student'

    return jsonify({
        'status': 'success',
        'message': 'Регистрация успешна!',
        'redirect': '/student'
    }), 200


# Вспомогательная функция для редиректа внутри Python
def redirect_to_role_page():
    role = session.get('role')
    if role == 'student': return redirect('/student')
    if role == 'cook': return redirect('/cook')
    if role == 'admin': return redirect('/admin')
    return redirect('/')


# ЗАПУСК
if __name__ == '__main__':
    app.run(debug=True)

# 1. API Логина (принимает данные из формы входа)
# Получаем данные из формы при входе.
@app.route('/api/login', methods=['POST'])
def api_login():
    # Получаем JSON, который прислал JS
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    print(f"Попытка входа: {username} / {password}") # Увидите это в терминале

    #ЗАГЛУШКА ЗАГЛУШКА ЗАГЛУШКА
    if username == 'student' and password == '123':
        return jsonify({
            'status': 'success',
            'message': 'Вход выполнен!',
            'role': 'student',
            'redirect': '/student' # адрес переадрисации
        }), 200
    elif username == 'cook' and password == '123':
        return jsonify({'status': 'success', 'role': 'cook', 'redirect': '/cook'}), 200
    else:
        # Не угадали логин или пароль
        return jsonify({'status': 'error', 'message': 'Неверный логин или пароль'}), 401
if __name__ == '__main__':
    app.run(debug=True)
