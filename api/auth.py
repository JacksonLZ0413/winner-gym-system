# -*- coding: utf-8 -*-
from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
import bcrypt
import json
import hashlib
import time
from functools import wraps
from . import api_bp
from .utils import get_db, success_response, error_response, row_to_dict
from config import Config

_login_fails = {}

def rate_limit(max_attempts=Config.RATE_LIMIT_MAX_ATTEMPTS, window=Config.RATE_LIMIT_WINDOW):
    def decorator(f):
        @wraps(f)
        def func(*args, **kwargs):
            ip = request.remote_addr or '127.0.0.1'
            now = time.time()
            if ip in _login_fails:
                cnt, t0 = _login_fails[ip]
                if now - t0 < window:
                    if cnt >= max_attempts:
                        return jsonify(error_response(f'登录失败次数过多，请 {int(window-(now-t0))+1} 秒后重试')), 429
                else:
                    _login_fails.pop(ip, None)
            return f(*args, **kwargs)
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

def hash_password(pwd):
    return bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(pwd, h):
    if not h:
        return False
    try:
        if bcrypt.checkpw(pwd.encode('utf-8'), h.encode('utf-8')):
            return True
    except:
        pass
    salt = Config.SECRET_KEY[:16]
    old_hash = hashlib.sha256((salt + pwd).encode()).hexdigest()
    return old_hash == h

@api_bp.route('/login', methods=['POST'])
@api_bp.route('/auth/login', methods=['POST'])
@rate_limit()
def api_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        on_login_fail()
        return jsonify(error_response('用户名和密码不能为空')), 400
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and verify_password(password, user['password'] or ''):
        # 检查用户角色，只允许用户登录
        if user['role'] != 'user':
            on_login_fail()
            return jsonify(error_response('该账号类型不支持小程序登录')), 403
        
        on_login_ok()
        access_token = create_access_token(
            identity=json.dumps({'user_id': user['id'], 'username': user['username'], 'role': user['role']}),
            expires_delta=timedelta(days=7)
        )
        return jsonify(success_response({
            'token': access_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role'],
                'phone': user['phone'],
                'course_quota': user['course_quota'] or 0,
                'avatar': user['avatar'] or ''
            }
        }))
    
    on_login_fail()
    return jsonify(error_response('用户名或密码错误')), 401

@api_bp.route('/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    
    if not username or not password or not name:
        return jsonify(error_response('用户名、密码、姓名为必填项')), 400
    
    if len(password) < 6:
        return jsonify(error_response('密码至少6位')), 400
    
    conn = get_db()
    try:
        # 强制设置为user角色，小程序端只允许用户注册
        conn.execute(
            'INSERT INTO users (username, password, name, phone, role, course_quota) VALUES (?, ?, ?, ?, ?, ?)',
            (username, hash_password(password), name, phone, 'user', 0)
        )
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        access_token = create_access_token(
            identity=json.dumps({'user_id': user['id'], 'username': user['username'], 'role': user['role']}),
            expires_delta=timedelta(days=7)
        )
        conn.close()
        return jsonify(success_response({
            'token': access_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role'],
                'phone': user['phone'],
                'course_quota': 0,
                'avatar': ''
            }
        }, '注册成功'))
    except Exception as e:
        conn.close()
        return jsonify(error_response('用户名已存在')), 400

@api_bp.route('/wechat/login', methods=['POST'])
@api_bp.route('/auth/wx_login', methods=['POST'])
def wechat_login():
    print("=== 收到微信登录请求 ===")
    data = request.get_json() or {}
    code = data.get('code', '')
    print(f"code: {code}")
    
    if not code:
        return jsonify(error_response('缺少code参数')), 400
    
    conn = get_db()
    
    openid = 'mock_openid_' + code
    print(f"openid: {openid}")
    
    user = conn.execute('SELECT * FROM users WHERE openid = ?', (openid,)).fetchone()
    
    if user:
        # 检查用户角色，只允许用户登录
        if user['role'] != 'user':
            conn.close()
            print(f"拒绝非用户角色登录")
            return jsonify(error_response('该账号类型不支持小程序登录')), 403
        
        print(f"找到用户: {user['name']}")
        access_token = create_access_token(
            identity=json.dumps({'user_id': user['id'], 'username': user['username'], 'role': user['role']}),
            expires_delta=timedelta(days=7)
        )
        conn.close()
        print("返回成功响应")
        return jsonify(success_response({
            'token': access_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role'],
                'phone': user['phone'],
                'course_quota': user['course_quota'] or 0,
                'avatar': user['avatar'] or ''
            }
        }))
    
    try:
        # 创建新用户时，强制设置为user角色
        conn.execute(
            'INSERT INTO users (username, password, name, role, openid, course_quota) VALUES (?, ?, ?, ?, ?, ?)',
            (openid, hash_password('wechat123'), '微信用户', 'user', openid, 0)
        )
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE openid = ?', (openid,)).fetchone()
        print(f"创建新用户: {user['name']}")
        access_token = create_access_token(
            identity=json.dumps({'user_id': user['id'], 'username': user['username'], 'role': user['role']}),
            expires_delta=timedelta(days=7)
        )
        conn.close()
        print("返回成功响应(新用户)")
        return jsonify(success_response({
            'token': access_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role'],
                'phone': user['phone'],
                'course_quota': 0,
                'avatar': ''
            }
        }, '登录成功'))
    except Exception as e:
        conn.close()
        print(f"错误: {e}")
        return jsonify(error_response('登录失败')), 400

@api_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user_info():
    identity = json.loads(get_jwt_identity())
    # 验证角色，只允许用户访问
    if identity['role'] != 'user':
        return jsonify(error_response('该功能仅对会员开放')), 403
    user_id = identity['user_id']
    
    conn = get_db()
    user = conn.execute('SELECT id, username, name, role, phone, course_quota FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if user:
        used = conn.execute("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status IN ('confirmed','completed')", (user_id,)).fetchone()[0]
        conn.close()
        quota = user['course_quota'] or 0
        remain = max(0, quota - used) if quota > 0 else -1
        
        return jsonify(success_response({
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'role': user['role'],
            'phone': user['phone'],
            'course_quota': quota,
            'used_quota': used,
            'remain_quota': remain
        }))
    
    conn.close()
    return jsonify(error_response('用户不存在')), 404