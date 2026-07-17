# -*- coding: utf-8 -*-
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import json
from . import api_bp
from .utils import get_db, success_response, error_response, rows_to_list

@api_bp.route('/book', methods=['POST'])
@jwt_required()
def create_booking():
    identity = json.loads(get_jwt_identity())
    # 验证角色，只允许用户访问
    if identity['role'] != 'user':
        return jsonify(error_response('该功能仅对会员开放')), 403
    user_id = identity['user_id']
    
    data = request.get_json() or {}
    coach_id = data.get('coach_id')
    course_id = data.get('course_id')
    date = data.get('date')
    time_slot = data.get('time_slot')
    note = data.get('note', '').strip()
    
    if not date or not time_slot or not coach_id or not course_id:
        return jsonify(error_response('请选择课程、日期和时间段')), 400
    
    conn = get_db()
    
    user = conn.execute('SELECT course_quota FROM users WHERE id=?', (user_id,)).fetchone()
    quota = user['course_quota'] or 0
    used = conn.execute("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status IN ('confirmed','completed')", (user_id,)).fetchone()[0]
    
    if quota > 0 and used >= quota:
        conn.close()
        return jsonify(error_response('您的课程配额已用完')), 400
    
    exist = conn.execute('''
        SELECT id FROM bookings WHERE coach_id=? AND date=? AND time_slot=?
        AND status NOT IN ('cancelled','rejected')
    ''', (coach_id, date, time_slot)).fetchone()
    
    if exist:
        conn.close()
        return jsonify(error_response('该时间段已被预约')), 400
    
    conn.execute('''
        INSERT INTO bookings (user_id, coach_id, course_id, date, time_slot, note, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    ''', (user_id, coach_id, course_id, date, time_slot, note))
    conn.commit()
    conn.close()
    
    return jsonify(success_response({}, '预约成功，等待教练确认'))

@api_bp.route('/bookings', methods=['GET'])
@jwt_required()
def get_user_bookings():
    identity = json.loads(get_jwt_identity())
    # 验证角色，只允许用户访问
    if identity['role'] != 'user':
        return jsonify(error_response('该功能仅对会员开放')), 403
    user_id = identity['user_id']
    
    conn = get_db()
    bookings = conn.execute('''
        SELECT b.*, c.specialty, u.name as coach_name, co.name as course_name,
               COALESCE(co.price, c.price, 0) as price
        FROM bookings b
        JOIN coaches c ON b.coach_id = c.id
        JOIN users u ON c.user_id = u.id
        LEFT JOIN courses co ON b.course_id = co.id
        WHERE b.user_id = ?
        ORDER BY b.date DESC, b.time_slot DESC
    ''', (user_id,)).fetchall()
    conn.close()
    
    return jsonify(success_response(rows_to_list(bookings)))

@api_bp.route('/booking/<int:booking_id>', methods=['DELETE'])
@jwt_required()
def cancel_booking(booking_id):
    identity = json.loads(get_jwt_identity())
    # 验证角色，只允许用户访问
    if identity['role'] != 'user':
        return jsonify(error_response('该功能仅对会员开放')), 403
    user_id = identity['user_id']
    
    conn = get_db()
    booking = conn.execute('SELECT * FROM bookings WHERE id=? AND user_id=?',
                          (booking_id, user_id)).fetchone()
    
    if not booking:
        conn.close()
        return jsonify(error_response('预约不存在')), 404
    
    conn.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
    conn.commit()
    conn.close()
    
    return jsonify(success_response({}, '预约已取消'))

@api_bp.route('/booking/<int:booking_id>/rate', methods=['POST'])
@jwt_required()
def rate_booking(booking_id):
    identity = json.loads(get_jwt_identity())
    # 验证角色，只允许用户访问
    if identity['role'] != 'user':
        return jsonify(error_response('该功能仅对会员开放')), 403
    user_id = identity['user_id']
    
    data = request.get_json() or {}
    rating = int(data.get('rating', 5))
    review = data.get('review', '').strip()
    
    conn = get_db()
    conn.execute('UPDATE bookings SET rating=?, review=? WHERE id=? AND user_id=?',
                (rating, review, booking_id, user_id))
    
    cid = conn.execute('SELECT coach_id FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if cid:
        avg = conn.execute('SELECT AVG(rating) FROM bookings WHERE coach_id=? AND rating IS NOT NULL',
                          (cid[0],)).fetchone()[0]
        cnt = conn.execute('SELECT COUNT(*) FROM bookings WHERE coach_id=? AND rating IS NOT NULL',
                          (cid[0],)).fetchone()[0]
        conn.execute('UPDATE coaches SET rating=?, rating_count=? WHERE id=?',
                    (round(avg, 1), cnt, cid[0]))
    
    conn.commit()
    conn.close()
    
    return jsonify(success_response({}, '评价成功'))