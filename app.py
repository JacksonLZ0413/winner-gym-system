# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, url_for, session, jsonify
from config import Config
from auth import init_auth_routes, get_db, csrf_context
from flask_jwt_extended import JWTManager
import sqlite3
import os

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# JWT配置
app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = Config.JWT_ACCESS_TOKEN_EXPIRES
jwt = JWTManager(app)

# 配置JWT错误响应格式
@jwt.unauthorized_loader
def unauthorized_response(callback):
    return jsonify({
        'code': 401,
        'message': '请先登录',
        'data': None
    }), 401

@jwt.invalid_token_loader
def invalid_token_response(callback):
    return jsonify({
        'code': 401,
        'message': 'token无效',
        'data': None
    }), 401

@jwt.expired_token_loader
def expired_token_response(callback):
    return jsonify({
        'code': 401,
        'message': 'token已过期',
        'data': None
    }), 401

# 添加CORS头部
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# 注册上下文处理器
@app.context_processor
def csrf_processor():
    return csrf_context()

# 初始化路由
init_auth_routes(app)
from booking import init_booking_routes
init_booking_routes(app)
from coach import init_coach_routes
init_coach_routes(app)
from stats import init_stats_routes
init_stats_routes(app)
from admin import init_admin_routes
init_admin_routes(app)
from feedback import init_feedback_routes
init_feedback_routes(app)

# 注册API路由（小程序专用）
from api import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# ── 路由 ────────────────────────────────────────────────────────
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

# ── 数据库初始化 ────────────────────────────────────────────────
def init_database():
    from database import init_db
    if not os.path.exists(Config.DB_PATH):
        init_db()

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5001, debug=True)
