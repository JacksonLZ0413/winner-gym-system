# -*- coding: utf-8 -*-
from flask import render_template, request, redirect, url_for, session, flash, send_file
from auth import get_db, validate_csrf
import csv
import io
from datetime import datetime, timedelta

# ── 数据统计功能 ────────────────────────────────────────────────────
def init_stats_routes(app):
    @app.route('/admin/stats')
    def admin_stats():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        conn = get_db()
        
        # 基本统计数据
        stats = {
            'total_users': conn.execute('SELECT COUNT(*) FROM users WHERE role = "user"').fetchone()[0],
            'total_coaches': conn.execute('SELECT COUNT(*) FROM users WHERE role = "coach"').fetchone()[0],
            'total_bookings': conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],
            'pending_bookings': conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "pending"').fetchone()[0],
            'completed_bookings': conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "completed"').fetchone()[0],
            'total_reviews': conn.execute('SELECT COUNT(*) FROM bookings WHERE rating IS NOT NULL').fetchone()[0],
            'avg_rating': conn.execute('SELECT AVG(rating) FROM bookings WHERE rating IS NOT NULL').fetchone()[0] or 0,
        }
        
        # 近30天预约趋势
        booking_trend = []
        for i in range(30):
            date = (datetime.now() - timedelta(days=29 - i)).strftime('%Y-%m-%d')
            count = conn.execute('SELECT COUNT(*) FROM bookings WHERE date = ?', (date,)).fetchone()[0]
            booking_trend.append({'date': date, 'count': count})
        
        # 教练预约统计
        coach_stats = conn.execute('''
            SELECT c.id, u.name, COUNT(b.id) as booking_count, AVG(b.rating) as avg_rating
            FROM coaches c
            JOIN users u ON c.user_id = u.id
            LEFT JOIN bookings b ON c.id = b.coach_id
            GROUP BY c.id
            ORDER BY booking_count DESC
        ''').fetchall()
        
        # 课程类型统计
        course_stats = conn.execute('''
            SELECT co.name, COUNT(b.id) as booking_count
            FROM courses co
            LEFT JOIN bookings b ON co.id = b.course_id
            GROUP BY co.id
            ORDER BY booking_count DESC
        ''').fetchall()
        
        # 会员等级统计（暂时注释，因为已删除会员等级功能）
        level_stats = []
        
        conn.close()
        return render_template('admin_stats.html', stats=stats, booking_trend=booking_trend, coach_stats=coach_stats, course_stats=course_stats, level_stats=level_stats)

    @app.route('/admin/export_stats', methods=['POST'])
    def export_stats():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        if validate_csrf():
            return redirect(url_for('admin_stats'))

        export_type = request.form.get('export_type')
        
        if export_type == 'bookings':
            return export_bookings_stats()
        elif export_type == 'coaches':
            return export_coaches_stats()
        elif export_type == 'users':
            return export_users_stats()
        else:
            flash('导出类型无效', 'error')
            return redirect(url_for('admin_stats'))

# ── 导出功能 ────────────────────────────────────────────────────
def export_bookings_stats():
    """导出预约统计数据"""
    conn = get_db()
    bookings = conn.execute('''
        SELECT b.id, u.name as user_name, c.name as coach_name, co.name as course_name, b.date, b.time_slot, b.status, b.rating, b.created_at
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN coaches c2 ON b.coach_id = c2.id
        JOIN users c ON c2.user_id = c.id
        LEFT JOIN courses co ON b.course_id = co.id
        ORDER BY b.date DESC, b.time_slot DESC
    ''').fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['预约ID', '用户', '教练', '课程', '日期', '时间', '状态', '评分', '创建时间'])
    for booking in bookings:
        writer.writerow([
            booking[0], booking[1], booking[2], booking[3], booking[4],
            booking[5], booking[6], booking[7] or '-', booking[8]
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'bookings_stats_{datetime.now().strftime("%Y%m%d")}.csv'
    )

def export_coaches_stats():
    """导出教练统计数据"""
    conn = get_db()
    coaches = conn.execute('''
        SELECT u.name, c.bio, c.specialty, c.experience, c.rating, c.rating_count,
               COUNT(b.id) as booking_count
        FROM coaches c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN bookings b ON c.id = b.coach_id
        GROUP BY c.id
        ORDER BY booking_count DESC
    ''').fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['教练姓名', '简介', '擅长', '经验', '评分', '评价次数', '预约次数'])
    for coach in coaches:
        writer.writerow([
            coach[0], coach[1] or '-', coach[2] or '-', coach[3],
            coach[4] or '-', coach[5], coach[6]
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'coaches_stats_{datetime.now().strftime("%Y%m%d")}.csv'
    )

def export_users_stats():
    """导出用户统计数据"""
    conn = get_db()
    users = conn.execute('''
        SELECT u.name, u.username, u.phone, u.course_quota,
               COUNT(b.id) as booking_count
        FROM users u
        LEFT JOIN bookings b ON u.id = b.user_id
        WHERE u.role = "user"
        GROUP BY u.id
        ORDER BY u.id DESC
    ''').fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['用户姓名', '用户名', '电话', '课程配额', '预约次数'])
    for user in users:
        writer.writerow([
            user[0], user[1], user[2] or '-', user[3], user[4]
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'users_stats_{datetime.now().strftime("%Y%m%d")}.csv'
    )
