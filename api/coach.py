# -*- coding: utf-8 -*-
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from . import api_bp
from .utils import get_db, success_response, error_response, rows_to_list

@api_bp.route('/coaches', methods=['GET'])
def get_coaches():
    conn = get_db()
    coaches = conn.execute('''
        SELECT c.*, u.name
        FROM coaches c
        JOIN users u ON c.user_id = u.id
    ''').fetchall()
    conn.close()
    
    return jsonify(success_response(rows_to_list(coaches)))

@api_bp.route('/coach/<int:coach_id>', methods=['GET'])
def get_coach_detail(coach_id):
    conn = get_db()
    
    coach = conn.execute('''
        SELECT c.*, u.name
        FROM coaches c
        JOIN users u ON c.user_id = u.id
        WHERE c.id = ?
    ''', (coach_id,)).fetchone()
    
    if not coach:
        conn.close()
        return jsonify(error_response('教练不存在')), 404
    
    courses = conn.execute('''
        SELECT c.*
        FROM courses c
        JOIN coach_courses cc ON c.id = cc.course_id
        WHERE cc.coach_id = ?
    ''', (coach_id,)).fetchall()
    
    reviews = conn.execute('''
        SELECT b.rating, b.review, b.created_at, u.name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.coach_id = ? AND b.rating IS NOT NULL
        ORDER BY b.created_at DESC LIMIT 10
    ''', (coach_id,)).fetchall()
    
    today = datetime.now().date()
    week_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    bookings = conn.execute('''
        SELECT date, time_slot FROM bookings
        WHERE coach_id = ? AND date >= ? AND status NOT IN ('cancelled','rejected')
    ''', (coach_id, today.strftime('%Y-%m-%d'))).fetchall()
    
    booked = {(b['date'], b['time_slot']) for b in bookings}
    
    all_slots = []
    seen = set()
    for date_str in week_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday = date_obj.weekday() + 1
        ranges = conn.execute('''
            SELECT start_time, end_time FROM time_slots
            WHERE coach_id = ? AND weekday = ? ORDER BY start_time
        ''', (coach_id, weekday)).fetchall()
        for tr in ranges:
            sh = int(tr['start_time'].split(':')[0])
            eh = int(tr['end_time'].split(':')[0])
            for h in range(sh, eh):
                ts = f"{h:02d}:00"
                key = (date_str, ts)
                if key not in seen:
                    seen.add(key)
                    all_slots.append({'date': date_str, 'time': ts, 'booked': (date_str, ts) in booked})
    
    conn.close()
    
    return jsonify(success_response({
        'coach': dict(coach),
        'courses': rows_to_list(courses),
        'reviews': rows_to_list(reviews),
        'week_dates': week_dates,
        'time_slots': all_slots
    }))

@api_bp.route('/courses', methods=['GET'])
def get_courses():
    conn = get_db()
    courses = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    
    return jsonify(success_response(rows_to_list(courses)))