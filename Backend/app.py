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
app.secret_key = 'secretKey123'


def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def format_user_id(uid):
    return str(uid).zfill(8)


def redirect_to_role_page():
    role = session.get('role')
    if role == 'student': return redirect('/student')
    if role == 'cook': return redirect('/cook')
    if role == 'admin': return redirect('/admin')
    return redirect('/login')


def check_subscription(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT subscription_end_date FROM users WHERE id=?', (user_id,)).fetchone()
    conn.close()
    if user and user['subscription_end_date']:
        try:
            return datetime.strptime(user['subscription_end_date'], '%Y-%m-%d').date() >= date.today()
        except:
            return False
    return False


@app.route('/')
def index(): return render_template('index.html')


@app.route('/login')
def login(): return redirect_to_role_page() if 'user_id' in session else render_template('login.html')


@app.route('/register')
def register(): return redirect_to_role_page() if 'user_id' in session else render_template('login.html')


@app.route('/student')
def student_dashboard(): return redirect('/login') if 'user_id' not in session else render_template('student.html')


@app.route('/cook')
def cook_dashboard(): return redirect('/login') if 'user_id' not in session else render_template('cook.html')


@app.route('/admin')
def admin_dashboard(): return redirect('/login') if 'user_id' not in session else render_template('admin.html')


@app.route('/logout')
def logout(): session.clear(); return redirect('/login')


@app.route('/css/<path:filename>')
def serve_css(filename): return send_from_directory(os.path.join(frontend_dir, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename): return send_from_directory(os.path.join(frontend_dir, 'js'), filename)


@app.route('/assets/<path:filename>')
def serve_assets(filename): return send_from_directory(os.path.join(frontend_dir, 'assets'), filename)


@app.route('/api/login', methods=['POST'])
def api_login():
    data = flask_request.get_json()
    u = data.get('username', '').strip()
    p = data.get('password')
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id=?', (int(u),)).fetchone() if u.isdigit() else conn.execute(
        'SELECT * FROM users WHERE email=? OR username=?', (u, u)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], p):
        session['user_id'] = user['id'];
        session['role'] = user['role']
        return jsonify({'status': 'success', 'redirect': f"/{user['role']}"})
    return jsonify({'status': 'error', 'message': 'Ошибка входа'}), 401


@app.route('/api/register', methods=['POST'])
def api_register():
    data = flask_request.get_json()
    conn = get_db_connection()
    if conn.execute('SELECT id FROM users WHERE email=?', (data['email'],)).fetchone():
        conn.close();
        return jsonify({'status': 'error', 'message': 'Email занят'}), 400
    try:
        cur = conn.execute('INSERT INTO users (username, email, password_hash, role, balance) VALUES (?, ?, ?, ?, 0)',
                           (data['username'], data['email'], generate_password_hash(data['password']), 'student'))
        uid = cur.lastrowid
        for aid in data.get('allergens', []): conn.execute(
            'INSERT INTO allergens (user_id, ingredient_id) VALUES (?, ?)', (uid, aid))
        conn.commit()
    except:
        conn.close(); return jsonify({'status': 'error', 'message': 'Ошибка'}), 500
    conn.close();
    session['user_id'] = uid;
    session['role'] = 'student'
    return jsonify({'status': 'success', 'redirect': '/student'})


@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    conn = get_db_connection()
    u = conn.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    algs = conn.execute(
        'SELECT i.id, i.name FROM allergens a JOIN ingredients i ON a.ingredient_id=i.id WHERE user_id=?',
        (session['user_id'],)).fetchall()
    conn.close()
    return jsonify({'status': 'success', 'user': {
        'id': u['id'], 'formatted_id': format_user_id(u['id']), 'username': u['username'],
        'email': u['email'], 'role': u['role'], 'balance': u['balance'],
        'has_active_subscription': check_subscription(u['id']), 'subscription_end_date': u['subscription_end_date']
    }, 'allergens': [dict(r) for r in algs]})


@app.route('/api/payments/topup', methods=['POST'])
def topup():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    amt = flask_request.get_json().get('amount')
    conn = get_db_connection()
    conn.execute('UPDATE users SET balance = balance + ? WHERE id=?', (amt, session['user_id']))
    conn.execute('INSERT INTO payments (user_id, amount, type, status) VALUES (?, ?, "topup", "completed")',
                 (session['user_id'], amt))
    conn.commit();
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/payments/subscription', methods=['POST'])
def buy_sub():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    conn = get_db_connection()
    u = conn.execute('SELECT balance FROM users WHERE id=?', (session['user_id'],)).fetchone()
    if u['balance'] < 1500: conn.close(); return jsonify({'status': 'error', 'message': 'Мало средств'}), 400
    conn.execute('UPDATE users SET balance = balance - 1500, subscription_end_date=? WHERE id=?',
                 ((date.today() + timedelta(days=30)).isoformat(), session['user_id']))
    conn.execute('INSERT INTO payments (user_id, amount, type, status) VALUES (?, 1500, "subscription", "completed")',
                 (session['user_id'],))
    conn.commit();
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/menu/today', methods=['GET'])
def get_menu():
    conn = get_db_connection()
    items = conn.execute(
        'SELECT m.id, m.meal_type, m.dish_id, d.name as dish_name, d.calories, d.price, d.current_stock FROM menu m JOIN dishes d ON m.dish_id=d.id WHERE m.date=?',
        (date.today().isoformat(),)).fetchall()
    res = {'breakfast': [], 'lunch': []}
    for item in items:
        d = dict(item)
        ings = conn.execute(
            'SELECT i.id, i.name FROM dish_ingredients di JOIN ingredients i ON di.ingredient_id=i.id WHERE di.dish_id=?',
            (d['dish_id'],)).fetchall()
        d['ingredients'] = [dict(i) for i in ings]
        res[d['meal_type']].append(d)
    conn.close();
    return jsonify(res)


@app.route('/api/orders', methods=['POST'])
def create_order():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    data = flask_request.get_json()
    conn = get_db_connection()
    menu = conn.execute(
        'SELECT m.*, d.current_stock, d.price, d.id as dish_id FROM menu m JOIN dishes d ON m.dish_id=d.id WHERE m.id=?',
        (data['menu_id'],)).fetchone()
    if not menu or menu['current_stock'] <= 0: conn.close(); return jsonify(
        {'status': 'error', 'message': 'Нет в наличии'}), 400
    if conn.execute('SELECT id FROM orders WHERE user_id=? AND menu_id=?',
                    (session['user_id'], data['menu_id'])).fetchone(): conn.close(); return jsonify(
        {'status': 'error', 'message': 'Уже заказано'}), 400

    paid = 1 if check_subscription(session['user_id']) else 0
    if not paid:
        user = conn.execute('SELECT balance FROM users WHERE id=?', (session['user_id'],)).fetchone()
        if user['balance'] < menu['price']: conn.close(); return jsonify(
            {'status': 'error', 'message': 'Мало средств'}), 400
        conn.execute('UPDATE users SET balance = balance - ? WHERE id=?', (menu['price'], session['user_id']))

    try:
        conn.execute('UPDATE dishes SET current_stock = current_stock - 1 WHERE id=?', (menu['dish_id'],))
        cur = conn.execute(
            'INSERT INTO orders (user_id, menu_id, order_date, paid, collected) VALUES (?, ?, datetime("now","localtime"), ?, 0)',
            (session['user_id'], data['menu_id'], paid))
        if not paid: conn.execute(
            'INSERT INTO payments (user_id, amount, type, order_id, status) VALUES (?, ?, "single", ?, "completed")',
            (session['user_id'], menu['price'], cur.lastrowid))
        conn.commit()
    except Exception as e:
        conn.close(); return jsonify({'status': 'error', 'message': str(e)}), 500
    conn.close();
    return jsonify({'status': 'success', 'message': 'Заказ создан'})


@app.route('/api/orders/my', methods=['GET'])
def get_my_orders():
    if 'user_id' not in session: return jsonify({'status': 'error'}), 401
    conn = get_db_connection()
    orders = conn.execute(
        'SELECT o.id, o.order_date as date, d.name as dish_name, d.price, o.paid, o.collected, d.id as dish_id FROM orders o JOIN menu m ON o.menu_id=m.id JOIN dishes d ON m.dish_id=d.id WHERE o.user_id=? ORDER BY o.order_date DESC',
        (session['user_id'],)).fetchall()
    conn.close();
    return jsonify([dict(o) for o in orders])


@app.route('/api/user/allergens', methods=['POST'])
def update_allergens():
    data = flask_request.get_json()
    conn = get_db_connection();
    conn.execute('DELETE FROM allergens WHERE user_id=?', (session['user_id'],))
    for aid in data.get('allergen_ids', []): conn.execute(
        'INSERT INTO allergens (user_id, ingredient_id) VALUES (?, ?)', (session['user_id'], aid))
    conn.commit();
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/reviews', methods=['POST'])
def add_review():
    d = flask_request.get_json()
    conn = get_db_connection();
    conn.execute('INSERT INTO reviews (user_id, dish_id, rating, comment) VALUES (?, ?, ?, ?)',
                 (session['user_id'], d['dish_id'], d['rating'], d['comment']));
    conn.commit();
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    conn = get_db_connection()
    dishes = conn.execute('SELECT * FROM dishes').fetchall()
    res = []
    for d in dishes:
        dish = dict(d);
        dish['stock_quantity'] = dish['current_stock']
        c = conn.execute(
            "SELECT COUNT(o.id) as c FROM orders o JOIN menu m ON o.menu_id=m.id WHERE m.dish_id=? AND o.collected=0 AND date(o.order_date)=date('now','localtime')",
            (dish['id'],)).fetchone()['c']
        dish['reserved'] = c
        res.append(dish)
    conn.close();
    return jsonify(res)


@app.route('/api/ingredients', methods=['GET'])
def get_ingr():
    conn = get_db_connection();
    ings = conn.execute('SELECT * FROM ingredients').fetchall();
    conn.close();
    return jsonify([dict(i) for i in ings])


@app.route('/api/inventory/create_item', methods=['POST'])
def create_item():
    if session.get('role') != 'cook': return jsonify({'status': 'error'}), 403
    name = flask_request.form.get('name', '').strip()
    stock = flask_request.form.get('stock', 0)
    item_type = flask_request.form.get('type')

    if not name: return jsonify({'status': 'error', 'message': 'Имя обязательно'}), 400
    conn = get_db_connection()
    try:
        if item_type == 'dish':
            if conn.execute('SELECT id FROM dishes WHERE name=?', (name,)).fetchone(): return jsonify(
                {'status': 'error', 'message': 'Дубликат'}), 400
            file = flask_request.files.get('image');
            img_url = ''
            if file and file.filename:
                fn = secure_filename(file.filename);
                file.save(os.path.join(frontend_dir, 'assets', fn));
                img_url = f'/assets/{fn}'

            cur = conn.execute(
                'INSERT INTO dishes (name, current_stock, calories, price, image_url) VALUES (?, ?, ?, ?, ?)',
                (name, stock, flask_request.form.get('calories'), flask_request.form.get('price'), img_url))

            ings_json = flask_request.form.get('ingredients', '[]')
            try:
                for iid in json.loads(ings_json): conn.execute(
                    'INSERT INTO dish_ingredients (dish_id, ingredient_id, quantity) VALUES (?, ?, 1)',
                    (cur.lastrowid, iid))
            except:
                pass
        else:
            if conn.execute('SELECT id FROM ingredients WHERE name=?', (name,)).fetchone(): return jsonify(
                {'status': 'error', 'message': 'Дубликат'}), 400
            conn.execute(
                'INSERT INTO ingredients (name, current_quantity, unit, min_quantity, price_per_unit) VALUES (?, ?, ?, ?, 0)',
                (name, stock, flask_request.form.get('unit'), flask_request.form.get('min_quantity')))
        conn.commit()
    except Exception as e:
        conn.close(); return jsonify({'status': 'error', 'message': str(e)}), 500
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/inventory/update', methods=['POST'])
def update_inv():
    if session.get('role') not in ['cook', 'admin']: return jsonify({'status': 'error'}), 403
    d = flask_request.get_json();
    conn = get_db_connection()
    try:
        if d['type'] == 'dish':
            conn.execute('UPDATE dishes SET current_stock=? WHERE id=?', (d['quantity'], d['id']))
        else:
            if d.get('min_quantity') is not None:
                conn.execute('UPDATE ingredients SET current_quantity=?, min_quantity=? WHERE id=?',
                             (d['quantity'], d['min_quantity'], d['id']))
            else:
                conn.execute('UPDATE ingredients SET current_quantity=? WHERE id=?', (d['quantity'], d['id']))
        conn.commit()
    except Exception as e:
        conn.close(); return jsonify({'status': 'error', 'message': str(e)}), 500
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/issue_meal', methods=['POST'])
def issue_meal():
    d = flask_request.get_json();
    dish_id = d.get('dish_id');
    ident = str(d.get('student_identifier')).strip()
    conn = get_db_connection()
    dish = conn.execute('SELECT * FROM dishes WHERE id=?', (dish_id,)).fetchone()
    if not dish or dish['current_stock'] <= 0: conn.close(); return jsonify(
        {'status': 'error', 'message': 'Нет в наличии'}), 400

    student = conn.execute('SELECT id, username FROM users WHERE id=?',
                           (int(ident),)).fetchone() if ident.isdigit() else conn.execute(
        'SELECT id, username FROM users WHERE email=? OR username=?', (ident, ident)).fetchone()
    if not student: conn.close(); return jsonify({'status': 'error', 'message': 'Ученик не найден'}), 404

    try:
        conn.execute('UPDATE dishes SET current_stock = current_stock - 1 WHERE id=?', (dish_id,))
        today = date.today().isoformat()
        menu = conn.execute('SELECT id FROM menu WHERE date=? AND dish_id=?', (today, dish_id)).fetchone()
        mid = menu['id'] if menu else conn.execute("INSERT INTO menu (date, meal_type, dish_id) VALUES (?, 'lunch', ?)",
                                                   (today, dish_id)).lastrowid
        conn.execute(
            'INSERT INTO orders (user_id, menu_id, order_date, paid, collected) VALUES (?, ?, datetime("now","localtime"), 1, 1)',
            (student['id'], mid))
        conn.commit()
    except:
        conn.close(); return jsonify({'status': 'error', 'message': 'Ошибка'}), 500
    conn.close();
    return jsonify(
        {'status': 'success', 'message': f'Выдано {student["username"]}', 'new_stock': dish['current_stock'] - 1})


@app.route('/api/cook/check_orders', methods=['POST'])
def check_orders():
    ident = str(flask_request.get_json().get('student_identifier')).strip();
    conn = get_db_connection()
    student = conn.execute('SELECT id, username FROM users WHERE id=?',
                           (int(ident),)).fetchone() if ident.isdigit() else conn.execute(
        'SELECT id, username FROM users WHERE email=? OR username=?', (ident, ident)).fetchone()
    if not student: conn.close(); return jsonify({'status': 'error', 'message': 'Ученик не найден'}), 404
    orders = conn.execute(
        "SELECT o.id, d.name as dish_name, d.calories, m.meal_type FROM orders o JOIN menu m ON o.menu_id=m.id JOIN dishes d ON m.dish_id=d.id WHERE o.user_id=? AND o.collected=0 AND date(o.order_date)=date('now','localtime')",
        (student['id'],)).fetchall()
    conn.close();
    return jsonify({'status': 'success', 'student_name': student['username'],
                    'student_id_formatted': format_user_id(student['id']), 'orders': [dict(o) for o in orders]})


@app.route('/api/cook/finish_order', methods=['POST'])
def finish_order():
    conn = get_db_connection();
    conn.execute('UPDATE orders SET collected=1 WHERE id=?', (flask_request.get_json().get('order_id'),));
    conn.commit();
    conn.close();
    return jsonify({'status': 'success', 'message': 'Выдано'})


@app.route('/api/menu/full', methods=['GET'])
def get_full_menu():
    conn = get_db_connection();
    items = conn.execute(
        'SELECT m.id, m.meal_type, d.name as dish_name, d.id as dish_id FROM menu m JOIN dishes d ON m.dish_id=d.id WHERE m.date=?',
        (flask_request.args.get('date', date.today().isoformat()),)).fetchall();
    conn.close()
    return jsonify([dict(i) for i in items])


@app.route('/api/menu/add', methods=['POST'])
def add_menu_item():
    d = flask_request.get_json();
    conn = get_db_connection();
    conn.execute('INSERT INTO menu (date, meal_type, dish_id) VALUES (?, ?, ?)',
                 (d['date'], d['meal_type'], d['dish_id']));
    conn.commit();
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/menu/delete/<int:id>', methods=['DELETE'])
def del_menu_item(id):
    conn = get_db_connection();
    conn.execute('DELETE FROM menu WHERE id=?', (id,));
    conn.commit();
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/purchase_requests', methods=['GET', 'POST'])
def purchase_reqs():
    conn = get_db_connection()
    if flask_request.method == 'GET':
        r = conn.execute(
            'SELECT pr.id, i.name as ingredient_name, pr.quantity, i.unit, pr.status, pr.request_date, u.username as requester FROM purchase_requests pr JOIN ingredients i ON pr.ingredient_id=i.id JOIN users u ON pr.requested_by=u.id ORDER BY pr.request_date DESC LIMIT 50').fetchall()
        conn.close();
        return jsonify([dict(x) for x in r])
    d = flask_request.get_json()
    conn.execute(
        'INSERT INTO purchase_requests (ingredient_id, quantity, requested_by, status) VALUES (?, ?, ?, "pending")',
        (d['ingredient_id'], d['quantity'], session['user_id']));
    conn.commit();
    conn.close()
    return jsonify({'status': 'success'})


@app.route('/api/stats/cook', methods=['GET'])
def get_cook_stats():
    conn = get_db_connection()

    def cnt(mt, i): return conn.execute(
        f"SELECT COUNT(o.id) as c FROM orders o JOIN menu m ON o.menu_id=m.id WHERE o.{'collected=1' if i else 'paid=1'} AND date(o.order_date)=date('now','localtime') AND m.meal_type=?",
        (mt,)).fetchone()['c']

    stats = {'breakfast': {'issued': cnt('breakfast', 1), 'sold': cnt('breakfast', 0)},
             'lunch': {'issued': cnt('lunch', 1), 'sold': cnt('lunch', 0)}}
    top = conn.execute(
        "SELECT d.name, COUNT(o.id) as count FROM orders o JOIN menu m ON o.menu_id=m.id JOIN dishes d ON m.dish_id=d.id WHERE date(o.order_date)=date('now','localtime') GROUP BY d.name ORDER BY count DESC").fetchall()
    conn.close();
    return jsonify({'breakfast': stats['breakfast'], 'lunch': stats['lunch'],
                    'breakdown': [{'name': r['name'], 'count': r['count']} for r in top]})

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    conn = get_db_connection();
    att = conn.execute("SELECT COUNT(*) as c FROM orders WHERE date(order_date)=date('now','localtime')").fetchone()[
        'c'];
    rev = conn.execute(
        "SELECT SUM(amount) as s FROM payments WHERE status='completed' AND date(payment_date)=date('now','localtime')").fetchone()[
              's'] or 0;
    tot = conn.execute("SELECT COUNT(*) as c FROM orders WHERE collected=1").fetchone()['c']
    conn.close();
    return jsonify({'attendance_today': att, 'revenue_today': rev, 'total_issued': tot})


@app.route('/api/purchase_requests/<int:rid>', methods=['PUT'])
def update_req(rid):
    st = flask_request.get_json().get('status');
    conn = get_db_connection()
    conn.execute(
        'UPDATE purchase_requests SET status=?, approved_by=?, approved_date=datetime("now","localtime") WHERE id=?',
        (st, session['user_id'], rid))
    if st == 'approved':
        r = conn.execute('SELECT ingredient_id, quantity FROM purchase_requests WHERE id=?', (rid,)).fetchone()
        if r: conn.execute('UPDATE ingredients SET current_quantity=current_quantity+? WHERE id=?',
                           (r['quantity'], r['ingredient_id']))
    conn.commit();
    conn.close();
    return jsonify({'status': 'success'})


@app.route('/api/admin/reports', methods=['GET'])
def get_reports():
    conn = get_db_connection();
    reps = conn.execute(
        "SELECT date(payment_date) as date, SUM(amount) as revenue, COUNT(*) as transactions FROM payments WHERE status='completed' GROUP BY date(payment_date) ORDER BY date DESC LIMIT 7").fetchall();
    conn.close()
    return jsonify([dict(r) for r in reps])


@app.route('/api/admin/users', methods=['GET'])
def get_users():
    conn = get_db_connection();
    users = conn.execute(
        'SELECT u.id, u.username, u.email, u.role, u.subscription_end_date, u.created_at, (SELECT COUNT(*) FROM orders WHERE user_id=u.id) as total_orders FROM users u').fetchall();
    conn.close()
    return jsonify([dict(r) for r in users])


@app.route('/api/admin/users/<int:uid>', methods=['PUT'])
def update_role(uid):
    conn = get_db_connection();
    conn.execute('UPDATE users SET role=? WHERE id=?', (flask_request.get_json().get('role'), uid));
    conn.commit();
    conn.close()
    return jsonify({'status': 'success'})


@app.route('/api/admin/active-subscriptions', methods=['GET'])
def get_active_subs():
    conn = get_db_connection();
    c = conn.execute("SELECT COUNT(*) as c FROM users WHERE subscription_end_date >= date('now')").fetchone()['c'];
    conn.close();
    return jsonify({'count': c})


@app.route('/api/admin/popular-dishes', methods=['GET'])
def get_pop():
    conn = get_db_connection();
    top = conn.execute(
        "SELECT d.name, COUNT(o.id) as count FROM orders o JOIN menu m ON o.menu_id=m.id JOIN dishes d ON m.dish_id=d.id WHERE date(o.order_date)=date('now', 'localtime') GROUP BY d.name ORDER BY count DESC LIMIT 5").fetchall();
    conn.close()
    return jsonify([{'name': r['name'], 'count': r['count'],
                     'percentage': int((r['count'] / (sum([x['count'] for x in top]) or 1)) * 100)} for r in top])


if __name__ == '__main__':
    app.run(debug=True)
