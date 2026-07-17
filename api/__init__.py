# -*- coding: utf-8 -*-
from flask import Blueprint
from flask_cors import CORS

api_bp = Blueprint('api', __name__)

CORS(api_bp, supports_credentials=True)

from . import auth, coach, booking


# 添加统计接口
from flask import jsonify
from .utils import get_db, success_response
from datetime import datetime, timedelta

@api_bp.route('/admin/stats', methods=['GET'])
def api_admin_stats():
    """小程序使用的统计数据接口"""
    conn = get_db()
    
    # 基本统计数据
    stats = {
        'total_users': conn.execute('SELECT COUNT(*) FROM users WHERE role = "user"').fetchone()[0],
        'total_coaches': conn.execute('SELECT COUNT(*) FROM users WHERE role = "coach"').fetchone()[0],
        'total_bookings': conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],
        'pending_bookings': conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "pending"').fetchone()[0],
        'completed_bookings': conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "completed"').fetchone()[0],
    }
    
    conn.close()
    return jsonify(success_response(stats))