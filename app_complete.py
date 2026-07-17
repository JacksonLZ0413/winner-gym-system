# 健身房预约系统 - 完整修复版
# 包含所有新功能：经营大屏、教练课时统计、学员记录、月报导出
# 修复了: CSRF、密码哈希、数据库字段名等问题

# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
import sqlite3
import os
import secrets
import hashlib
import time
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'gym_coach_secret_key_2024_fixed'
DB_PATH = os.path.join(os.path.dirname(__file__), 'gym.db')

# ── 简单限流 ──────────────────────────────────────────────────
_login_fails = {}

def rate_limit(max_attempts=5, window=300):
    def decorator(f):
        @wraps(f)
        def func(*args, **kwargs):
            ip = request.remote_addr or '127.0.0.1'
            now = time.time()
            if ip in _login_fails:
                cnt, t0 = _login_fails[ip]
                if now - t0 < window:
                    if cnt >= max_attempts:
                        flash(f'登录失败次数过多，请 {int(window-(now-t0))+1} 秒后重试', 'error')
                        return redirect(url_for('login'))
                else:
                    _login_fails.pop(ip, None)
            result = f(*args, **kwargs)
            return result
        return func
    return decorator

def on_login_fail():
    ip = request.remote_addr or '127.0.0.1'
    now = time.time()
    cnt, t0 = _login_fails.get(ip, (0, now))
    _login_fails[ip] = (cnt + 1, t0)

def on_login_ok():
    ip = request.remote_addr or '127.0.0.1'
    _login_fails.pop(ip, None)

# ── 密码工具 ──────────────────────────────────────────────────
def hash_password(pwd):
    salt = app.secret_key[:16]
    return hashlib.sha256((salt + pwd).encode()).hexdigest()

def verify_password(pwd, h):
    return hash_password(pwd) == h

# ── HTML转义 ─────────────────────────────────────────────────
def escape(s):
    if s is None:
        return ''
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# ── CSRF Token ────────────────────────────────────────────────
def make_csrf_token():
    return secrets.token_hex(16)

@app.context_processor
def csrf_context():
    if '_csrf' not in session:
        session['_csrf'] = make_csrf_token()
    return dict(csrf_token=session.get('_csrf'))

def validate_csrf():
    token = request.form.get('_csrf') or request.headers.get('X-CSRF-Token','')
    if token != session.get('_csrf'):
        flash('表单已过期，请刷新页面重试', 'error')
        return True
    session['_csrf'] = make_csrf_token()
    return False

# ── 数据库 ─────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    from database import init_db
    if not os.path.exists(DB_PATH):
        init_db()
    conn = get_db()
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in c.fetchall()]
    if 'password_hash' not in cols:
        c.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        users = conn.execute('SELECT id, password FROM users').fetchall()
        for uid, pwd in users:
            conn.execute('UPDATE users SET password_hash=? WHERE id=?', (hash_password(pwd), uid))
        conn.commit()
        print('密码已加密升级')
    conn.close()

# ── 路由 ───────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin'))
        elif session.get('role') == 'coach':
            return redirect(url_for('coach_dashboard'))
        else:
            return redirect(url_for('coaches'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@rate_limit()
def login():
    if request.method == 'POST':
        if validate_csrf():
            return redirect(url_for('login'))
        username = escape(request.form.get('username', '').strip())
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and verify_password(password, user['password_hash'] or ''):
            on_login_ok()
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=7)
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            flash(f'欢迎回来，{user["name"]}！', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            elif user['role'] == 'coach':
                return redirect(url_for('coach_dashboard'))
            else:
                return redirect(url_for('coaches'))
        else:
            on_login_fail()
            flash('用户名或密码错误', 'error')
    session['_csrf'] = make_csrf_token()
    return render_template('login.html', csrf_token=session['_csrf'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if validate_csrf():
            return redirect(url_for('register'))
        username = escape(request.form.get('username', '').strip())
        password = request.form.get('password', '')
        name = escape(request.form.get('name', '').strip())
        phone = escape(request.form.get('phone', '').strip())
        if not username or not password or not name:
            flash('用户名、密码、姓名为必填项', 'error')
            return redirect(url_for('register'))
        if len(password) < 6:
            flash('密码至少6位', 'error')
            return redirect(url_for('register'))
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password_hash, name, phone, role, course_quota) VALUES (?, ?, ?, ?, ?, ?)',
                        (username, hash_password(password), name, phone, 'user', 0))
            conn.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('用户名已存在', 'error')
        finally:
            conn.close()
    session['_csrf'] = make_csrf_token()
    return render_template('register.html', csrf_token=session['_csrf'])

@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'success')
    return redirect(url_for('index'))

# ── 教练列表 ───────────────────────────────────────────────────
@app.route('/coaches')
def coaches():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    coaches = conn.execute('SELECT c.*, u.name FROM coaches c JOIN users u ON c.user_id = u.id').fetchall()
    conn.close()
    return render_template('coaches.html', coaches=coaches)

# ── 教练详情 & 预约 ────────────────────────────────────────────
@app.route('/coach/<int:coach_id>', methods=['GET', 'POST'])
def coach_detail(coach_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    coach = conn.execute('SELECT c.*, u.name FROM coaches c JOIN users u ON c.user_id = u.id WHERE c.id = ?', (coach_id,)).fetchone()
    if not coach:
        conn.close()
        flash('教练不存在', 'error')
        return redirect(url_for('coaches'))
    reviews = conn.execute('SELECT b.rating, b.review, b.created_at, u.name FROM bookings b JOIN users u ON b.user_id = u.id WHERE b.coach_id = ? AND b.rating IS NOT NULL ORDER BY b.created_at DESC LIMIT 10', (coach_id,)).fetchall()
    today = datetime.now().date()
    week_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    bookings = conn.execute('SELECT date, time_slot FROM bookings WHERE coach_id = ? AND date >= ? AND status NOT IN ("cancelled","rejected")', (coach_id, today.strftime('%Y-%m-%d'))).fetchall()
    booked = {(b['date'], b['time_slot']) for b in bookings}
    all_slots = []
    for date_str in week_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday = date_obj.weekday() + 1
        ranges = conn.execute('SELECT start_time, end_time FROM time_slots WHERE coach_id = ? AND weekday = ? ORDER BY start_time', (coach_id, weekday)).fetchall()
        for tr in ranges:
            sh = int(tr['start_time'].split(':')[0])
            eh = int(tr['end_time'].split(':')[0])
            for h in range(sh, eh):
                ts = f"{h:02d}:00"
                all_slots.append({'date': date_str, 'time': ts, 'booked': (date_str, ts) in booked})
    conn.close()
    return render_template('coach.html', coach=coach, reviews=reviews, week_dates=week_dates, all_time_slots=all_slots)

# ── 预约课程 ───────────────────────────────────────────────────
@app.route('/book', methods=['POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if validate_csrf():
        return redirect(url_for('my_bookings'))
    coach_id = request.form.get('coach_id')
    date = request.form.get('date')
    time_slot = request.form.get('time_slot')
    note = escape(request.form.get('note', '').strip())
    if not date or not time_slot or not coach_id:
        flash('请选择日期和时间段', 'error')
        return redirect(url_for('coach_detail', coach_id=coach_id))
    conn = get_db()
    user = conn.execute('SELECT course_quota FROM users WHERE id=?', (session['user_id'],)).fetchone()
    quota = user['course_quota'] or 0
    used = conn.execute("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status IN ('confirmed','completed')", (session['user_id'],)).fetchone()[0]
    if quota > 0 and used >= quota:
        conn.close()
        flash('您的课程配额已用完，请联系管理员增加配额', 'error')
        return redirect(url_for('my_bookings'))
    exist = conn.execute('SELECT id FROM bookings WHERE coach_id=? AND date=? AND time_slot=? AND status NOT IN ("cancelled","rejected")', (coach_id, date, time_slot)).fetchone()
    if exist:
        conn.close()
        flash('该时间段已被预约', 'error')
        return redirect(url_for('coach_detail', coach_id=coach_id))
    conn.execute('INSERT INTO bookings (user_id, coach_id, date, time_slot, note, status) VALUES (?, ?, ?, ?, ?, "pending")', (session['user_id'], coach_id, date, time_slot, note))
    conn.commit()
    conn.close()
    flash('预约成功，等待教练确认', 'success')
    return redirect(url_for('my_bookings'))

# ── 我的预约 ───────────────────────────────────────────────────
@app.route('/my_bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    user = conn.execute('SELECT course_quota FROM users WHERE id=?', (session['user_id'],)).fetchone()
    used = conn.execute("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status IN ('confirmed','completed')", (session['user_id'],)).fetchone()[0]
    quota = user['course_quota'] or 0
    remain = max(0, quota - used) if quota > 0 else '无限制'
    bookings = conn.execute('SELECT b.*, c.specialty, u.name as coach_name FROM bookings b JOIN coaches c ON b.coach_id = c.id JOIN users u ON c.user_id = u.id WHERE b.user_id = ? ORDER BY b.date DESC, b.time_slot DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_bookings.html', bookings=bookings, quota=quota, used=used, remain=remain)

@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    b = conn.execute('SELECT * FROM bookings WHERE id=? AND user_id=?', (booking_id, session['user_id'])).fetchone()
    if b:
        conn.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
        conn.commit()
        flash('预约已取消', 'success')
    conn.close()
    return redirect(url_for('my_bookings'))

@app.route('/rate_booking', methods=['POST'])
def rate_booking():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if validate_csrf():
        return redirect(url_for('my_bookings'))
    bid = request.form.get('booking_id')
    rating = int(request.form.get('rating', 5))
    review = escape(request.form.get('review', '').strip())
    conn = get_db()
    conn.execute('UPDATE bookings SET rating=?, review=? WHERE id=? AND user_id=?', (rating, review, bid, session['user_id']))
    cid = conn.execute('SELECT coach_id FROM bookings WHERE id=?', (bid,)).fetchone()
    if cid:
        avg = conn.execute('SELECT AVG(rating) FROM bookings WHERE coach_id=? AND rating IS NOT NULL', (cid[0],)).fetchone()[0]
        cnt = conn.execute('SELECT COUNT(*) FROM bookings WHERE coach_id=? AND rating IS NOT NULL', (cid[0],)).fetchone()[0]
        conn.execute('UPDATE coaches SET rating=?, rating_count=? WHERE id=?', (round(avg, 1), cnt, cid[0]))
    conn.commit()
    conn.close()
    flash('评价成功，感谢您的反馈！', 'success')
    return redirect(url_for('my_bookings'))

# ── 教练后台 ───────────────────────────────────────────────────
@app.route('/coach_dashboard')
def coach_dashboard():
    if 'user_id' not in session or session.get('role') != 'coach':
        return redirect(url_for('login'))
    conn = get_db()
    coach = conn.execute('SELECT * FROM coaches WHERE user_id=?', (session['user_id'],)).fetchone()
    if not coach:
        conn.close()
        flash('教练信息不存在', 'error')
        return redirect(url_for('index'))
    today = datetime.now().strftime('%Y-%m-%d')
    bookings = conn.execute('SELECT b.*, u.name, u.phone FROM bookings b JOIN users u ON b.user_id = u.id WHERE b.coach_id = ? AND b.date >= ? ORDER BY b.date, b.time_slot', (coach['id'], today)).fetchall()
    reviews = conn.execute('SELECT b.rating, b.review, b.created_at, u.name FROM bookings b JOIN users u ON b.user_id = u.id WHERE b.coach_id = ? AND b.rating IS NOT NULL ORDER BY b.created_at DESC LIMIT 10', (coach['id'],)).fetchall()
    schedule = conn.execute('SELECT weekday, start_time, end_time FROM time_slots WHERE coach_id = ? ORDER BY weekday, start_time', (coach['id'],)).fetchall()
    conn.close()
    return render_template('coach_dashboard.html', coach=coach, bookings=bookings, reviews=reviews, schedule=schedule)

@app.route('/coach/respond', methods=['POST'])
def coach_respond():
    if 'user_id' not in session or session.get('role') != 'coach':
        return redirect(url_for('login'))
    if validate_csrf():
        return redirect(url_for('coach_dashboard'))
    bid = request.form.get('booking_id')
    action = request.form.get('action')
    conn = get_db()
    if action == 'confirm':
        conn.execute("UPDATE bookings SET status='confirmed' WHERE id=?", (bid,))
        flash('预约已确认', 'success')
    elif action == 'reject':
        conn.execute("UPDATE bookings SET status='rejected' WHERE id=?", (bid,))
        flash('预约已拒绝', 'success')
    elif action == 'complete':
        conn.execute("UPDATE bookings SET status='completed' WHERE id=?", (bid,))
        flash('课程已完成', 'success')
    conn.commit()
    conn.close()
    return redirect(url_for('coach_dashboard'))

# ── 管理员后台 ─────────────────────────────────────────────────
@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    stats = {
        'total_users': conn.execute('SELECT COUNT(*) FROM users WHERE role="user"').fetchone()[0],
        'total_coaches': conn.execute('SELECT COUNT(*) FROM coaches').fetchone()[0],
        'total_bookings': conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],
        'pending_bookings': conn.execute("SELECT COUNT(*) FROM bookings WHERE status='pending'").fetchone()[0],
    }
    recent = conn.execute('SELECT b.*, u.name as user_name, u2.name as coach_name FROM bookings b JOIN users u ON b.user_id = u.id JOIN coaches c ON b.coach_id = c.id JOIN users u2 ON c.user_id = u2.id ORDER BY b.created_at DESC LIMIT 20').fetchall()
    conn.close()
    return render_template('admin.html', stats=stats, recent_bookings=recent)

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/user/password', methods=['POST'])
def admin_change_user_password():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    if validate_csrf():
        return redirect(url_for('admin_users'))
    uid = request.form.get('user_id')
    pwd = request.form.get('new_password', '')
    if len(pwd) < 6:
        flash('密码至少6位', 'error')
    else:
        conn = get_db()
        conn.execute('UPDATE users SET password_hash=? WHERE id=?', (hash_password(pwd), uid))
        conn.commit()
        conn.close()
        flash('密码已修改', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/coaches')
def admin_coaches():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    coaches = conn.execute('SELECT c.*, u.name, u.username FROM coaches c JOIN users u ON c.user_id = u.id').fetchall()
    conn.close()
    return render_template('admin_coaches.html', coaches=coaches)

@app.route('/admin/coaches/add', methods=['POST'])
def admin_add_coach():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    if validate_csrf():
        return redirect(url_for('admin_coaches'))
    username = escape(request.form.get('username', '').strip())
    password = request.form.get('password', '')
    name = escape(request.form.get('name', '').strip())
    bio = escape(request.form.get('bio', '').strip())
    specialty = escape(request.form.get('specialty', '').strip())
    experience = request.form.get('experience', '1')
    if not username or not password or not name:
        flash('用户名、密码、姓名为必填项', 'error')
        return redirect(url_for('admin_coaches'))
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (username, password_hash, role, name) VALUES (?, ?, ?, ?)',
                    (username, hash_password(password), 'coach', name))
        user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.execute('INSERT INTO coaches (user_id, bio, specialty, experience, rating, rating_count) VALUES (?, ?, ?, ?, 5.0, 0)',
                    (user_id, bio, specialty, int(experience)))
        cid = conn.execute('SELECT id FROM coaches WHERE user_id=?', (user_id,)).fetchone()[0]
        for wd in range(1, 6):
            for s, e in [('09:00','12:00'),('14:00','18:00'),('19:00','21:00')]:
                conn.execute('INSERT INTO time_slots (coach_id, weekday, start_time, end_time) VALUES (?,?,?,?)', (cid, wd, s, e))
        conn.commit()
        flash(f'教练 {name} 添加成功', 'success')
    except sqlite3.IntegrityError:
        conn.rollback()
        flash('用户名已存在', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin_coaches'))

@app.route('/admin/coaches/delete/<int:coach_id>', methods=['POST'])
def admin_delete_coach(coach_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    if validate_csrf():
        return redirect(url_for('admin_coaches'))
    conn = get_db()
    coach = conn.execute('SELECT user_id FROM coaches WHERE id=?', (coach_id,)).fetchone()
    if coach:
        uid = coach['user_id']
        conn.execute('DELETE FROM time_slots WHERE coach_id=?', (coach_id,))
        conn.execute("UPDATE bookings SET status='cancelled' WHERE coach_id=?", (coach_id,))
        conn.execute('DELETE FROM coaches WHERE id=?', (coach_id,))
        conn.execute('DELETE FROM users WHERE id=?', (uid,))
        conn.commit()
        flash('教练已删除', 'success')
    conn.close()
    return redirect(url_for('admin_coaches'))

@app.route('/admin/users/courses')
def admin_user_courses():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    users = conn.execute('SELECT u.id, u.name, u.username, u.phone, COALESCE(u.course_quota,0) AS course_quota, COUNT(CASE WHEN b.status IN ("confirmed","completed") THEN 1 END) AS used FROM users u LEFT JOIN bookings b ON b.user_id = u.id WHERE u.role="user" GROUP BY u.id ORDER BY u.created_at DESC').fetchall()
    conn.close()
    return render_template('admin_user_courses.html', users=users)

@app.route('/admin/users/courses/update', methods=['POST'])
def admin_update_course_quota():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    if validate_csrf():
        return redirect(url_for('admin_user_courses'))
    uid = request.form.get('user_id')
    quota = max(0, int(request.form.get('quota', 0) or 0))
    conn = get_db()
    conn.execute('UPDATE users SET course_quota=? WHERE id=?', (quota, uid))
    conn.commit()
    conn.close()
    flash('课程配额已更新', 'success')
    return redirect(url_for('admin_user_courses'))

# ═══════════════════════════════════════════════════════════════
# 新增功能：教练课时统计
# ═══════════════════════════════════════════════════════════════
@app.route('/admin/stats/coaches')
def admin_coach_stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    year, mon = map(int, month.split('-'))
    start = f"{year}-{mon:02d}-01"
    end = f"{year+1}-01-01" if mon == 12 else f"{year}-{mon+1:02d}-01"
    conn = get_db()
    coaches = conn.execute('''
        SELECT c.id, u.name,
               COUNT(CASE WHEN b.status="completed" THEN 1 END) as completed,
               COUNT(CASE WHEN b.status="confirmed" THEN 1 END) as confirmed,
               COUNT(CASE WHEN b.status="pending" THEN 1 END) as pending,
               COUNT(CASE WHEN b.status IN ("cancelled","rejected") THEN 1 END) as cancelled,
               COUNT(b.id) as total
        FROM coaches c JOIN users u ON c.user_id = u.id
        LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ? AND b.date < ?
        GROUP BY c.id ORDER BY completed DESC
    ''', (start, end)).fetchall()
    conn.close()
    return render_template('admin_coach_stats.html', coaches=coaches, month=month)

# ═══════════════════════════════════════════════════════════════
# 新增功能：学员上课记录汇总
# ═══════════════════════════════════════════════════════════════
@app.route('/admin/member_records')
def admin_member_records():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db()
    members = conn.execute('''
        SELECT u.id, u.name, u.phone, COALESCE(u.course_quota,0) as quota,
               COUNT(CASE WHEN b.status IN ("confirmed","completed") THEN 1 END) as used,
               COUNT(CASE WHEN b.status="completed" THEN 1 END) as completed,
               MAX(b.date) as last_booking
        FROM users u LEFT JOIN bookings b ON b.user_id = u.id
        WHERE u.role = "user" GROUP BY u.id ORDER BY completed DESC
    ''').fetchall()
    conn.close()
    return render_template('admin_member_records.html', members=members)

# ═══════════════════════════════════════════════════════════════
# 新增功能：经营大屏
# ═══════════════════════════════════════════════════════════════
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    today = datetime.now().strftime('%Y-%m-%d')
    month_start = datetime.now().strftime('%Y-%m') + '-01'
    conn = get_db()
    stats = {
        'today_bookings': conn.execute("SELECT COUNT(*) FROM bookings WHERE date=?", (today,)).fetchone()[0],
        'today_completed': conn.execute("SELECT COUNT(*) FROM bookings WHERE date=? AND status='completed'", (today,)).fetchone()[0],
        'total_members': conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
        'total_coaches': conn.execute("SELECT COUNT(*) FROM coaches").fetchone()[0],
        'month_bookings': conn.execute("SELECT COUNT(*) FROM bookings WHERE date>=?", (month_start,)).fetchone()[0],
    }
    recent = conn.execute('''
        SELECT b.*, u.name as user_name, u2.name as coach_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN coaches c ON b.coach_id = c.id
        JOIN users u2 ON c.user_id = u2.id
        ORDER BY b.created_at DESC LIMIT 20
    ''').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', stats=stats, recent=recent, today=today)

# ═══════════════════════════════════════════════════════════════
# 新增功能：月报导出
# ═══════════════════════════════════════════════════════════════
@app.route('/admin/report/export')
def admin_export_report():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    year, mon = map(int, month.split('-'))
    start = f"{year}-{mon:02d}-01"
    end = f"{year+1}-01-01" if mon == 12 else f"{year}-{mon+1:02d}-01"
    conn = get_db()
    bookings = conn.execute('''
        SELECT b.date, b.time_slot, b.status, b.rating, u.name as member, u2.name as coach
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN coaches c ON b.coach_id = c.id
        JOIN users u2 ON c.user_id = u2.id
        WHERE b.date >= ? AND b.date < ?
        ORDER BY b.date, b.time_slot
    ''', (start, end)).fetchall()
    coaches = conn.execute('''
        SELECT u.name as coach_name,
               COUNT(CASE WHEN b.status="completed" THEN 1 END) as completed,
               COUNT(CASE WHEN b.status IN ("cancelled","rejected") THEN 1 END) as cancelled,
               COUNT(b.id) as total
        FROM coaches c JOIN users u ON c.user_id = u.id
        LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ? AND b.date < ?
        GROUP BY c.id ORDER BY completed DESC
    ''', (start, end)).fetchall()
    conn.close()
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f'{month} 健身房运营月报'])
    writer.writerow([])
    writer.writerow(['教练课时统计'])
    writer.writerow(['教练', '完成', '取消', '总计'])
    for c in coaches:
        writer.writerow([c['coach_name'], c['completed'], c['cancelled'], c['total']])
    writer.writerow([])
    writer.writerow(['预约明细'])
    writer.writerow(['日期', '时间', '学员', '教练', '状态', '评分'])
    for b in bookings:
        writer.writerow([b['date'], b['time_slot'], b['member'], b['coach'], b['status'], b['rating'] or '-'])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=gym_report_{month}.csv'})

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=80, debug=False)
