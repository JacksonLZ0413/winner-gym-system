# -*- coding: utf-8 -*-
from flask import render_template, request, redirect, url_for, session, flash
import sqlite3
import time
import secrets
import bcrypt
from functools import wraps
from datetime import timedelta
from config import Config

# HTML转义函数，防止XSS攻击
def escape(s):
    if s is None:
        return ''
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

# ── 简单限流：记录 IP 登录失败次数 ──────────────────────────────
_login_fails = {}   # { ip: (count, last_time) }

def rate_limit(max_attempts=Config.RATE_LIMIT_MAX_ATTEMPTS, window=Config.RATE_LIMIT_WINDOW):
    """5次失败后锁定5分钟"""
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

# ── 密码工具 ────────────────────────────────────────────────────
def hash_password(pwd):
    """使用 bcrypt 加密密码"""
    return bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def old_hash_password(pwd):
    """旧的 SHA-256 加密（用于兼容旧密码）"""
    import hashlib
    salt = Config.SECRET_KEY[:16]
    return hashlib.sha256((salt + pwd).encode()).hexdigest()

def verify_password(pwd, h):
    """验证密码，支持bcrypt和旧的SHA-256格式"""
    # 先尝试bcrypt验证
    try:
        if bcrypt.checkpw(pwd.encode('utf-8'), h.encode('utf-8')):
            return True
    except:
        pass
    
    # 再尝试旧的SHA-256验证
    import hashlib
    salt = Config.SECRET_KEY[:16]
    old_hash = hashlib.sha256((salt + pwd).encode()).hexdigest()
    return old_hash == h

# ── CSRF Token ─────────────────────────────────────────────────
def make_csrf_token():
    return secrets.token_hex(16)

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

# ── 数据库 ──────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── 认证路由 ────────────────────────────────────────────────────
def init_auth_routes(app):
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

            if user and verify_password(password, user['password'] or ''):
                # 检查是否使用的是旧的SHA-256密码，如果是，更新为bcrypt格式
                try:
                    # 尝试用bcrypt验证，如果失败，说明是旧密码
                    if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                        # 更新密码为bcrypt格式
                        new_hash = hash_password(password)
                        conn = get_db()
                        conn.execute('UPDATE users SET password=? WHERE id=?', (new_hash, user['id']))
                        conn.commit()
                        conn.close()
                except:
                    # 如果bcrypt验证失败（比如密码不是bcrypt格式），更新为bcrypt格式
                    new_hash = hash_password(password)
                    conn = get_db()
                    conn.execute('UPDATE users SET password=? WHERE id=?', (new_hash, user['id']))
                    conn.commit()
                    conn.close()
                
                on_login_ok()
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=Config.PERMANENT_SESSION_LIFETIME)
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
                conn.execute(
                    'INSERT INTO users (username, password, name, phone, role, course_quota) VALUES (?, ?, ?, ?, ?, ?)',
                    (username, hash_password(password), name, phone, 'user', 0)
                )
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

    @app.route('/change_password', methods=['GET', 'POST'])
    def change_password():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            if validate_csrf():
                return redirect(url_for('change_password'))

            old_pwd = request.form.get('old_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm = request.form.get('confirm_password', '')

            if not new_pwd or len(new_pwd) < 6:
                flash('新密码至少6位', 'error')
                return redirect(url_for('change_password'))

            if new_pwd != confirm:
                flash('两次输入的密码不一致', 'error')
                return redirect(url_for('change_password'))

            conn = get_db()
            user = conn.execute('SELECT password FROM users WHERE id=?',
                               (session['user_id'],)).fetchone()
            if not verify_password(old_pwd, user['password'] or ''):
                conn.close()
                flash('原密码错误', 'error')
                return redirect(url_for('change_password'))

            conn.execute('UPDATE users SET password=? WHERE id=?',
                         (hash_password(new_pwd), session['user_id']))
            conn.commit()
            conn.close()
            flash('密码修改成功！', 'success')
            return redirect(url_for('index'))

        session['_csrf'] = make_csrf_token()
        return render_template('change_password.html', csrf_token=session['_csrf'])
