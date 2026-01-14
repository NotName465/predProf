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

# 3. Маршруты (Routes) - привязываем URL к HTML файлам

@app.route('/')
def index():
    return render_template('index.html')

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