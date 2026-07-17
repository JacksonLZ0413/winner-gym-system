# -*- coding: utf-8 -*-
import sqlite3, os, csv, io
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, escape, Response

DB_PATH = os.path.join(os.path.dirname(__file__), 'gym.db')

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

# ── 教练课时统计 ──────────────────────────────────────────────
@app.route('/admin/stats/coaches')
def admin_coach_stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    year, mon = map(int, month.split('-'))
    start = f"{year}-{mon:02d}-01"
    if mon == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{mon+1:02d}-01"

    conn = db()
    coaches = conn.execute('''
        SELECT c.id, u.name,
               COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
               COUNT(CASE WHEN b.status='confirmed' THEN 1 END) as confirmed,
               COUNT(CASE WHEN b.status='pending' THEN 1 END) as pending,
               COUNT(CASE WHEN b.status='cancelled' OR b.status='rejected' THEN 1 END) as cancelled,
               COUNT(b.id) as total,
               COALESCE(AVG(CASE WHEN b.rating THEN b.rating END), 0) as avg_rating,
               COUNT(CASE WHEN b.rating THEN 1 END) as rated
        FROM coaches c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN bookings b ON b.coach_id = c.id
            AND b.date >= ? AND b.date < ?
        GROUP BY c.id
        ORDER BY completed DESC
    ''', (start, end)).fetchall()

    # 全局统计
    total_completed = sum(c['completed'] for c in coaches)
    total_confirmed = sum(c['confirmed'] for c in coaches)
    total_cancelled = sum(c['cancelled'] for c in coaches)

    # 月份列表（最近12个月）
    months = []
    d = datetime.now()
    for i in range(11, -1, -1):
        md = datetime(d.year, d.month, 1) - timedelta(days=i*32)
        months.append(md.strftime('%Y-%m'))

    conn.close()
    return render_template('admin_coach_stats.html',
                           coaches=coaches,
                           month=month,
                           months=months,
                           total_completed=total_completed,
                           total_confirmed=total_confirmed,
                           total_cancelled=total_cancelled)

# ── 学员上课记录汇总 ──────────────────────────────────────────
@app.route('/admin/stats/members')
def admin_member_records():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = db()
    members = conn.execute('''
        SELECT u.id, u.name, u.phone,
               COALESCE(u.course_quota, 0) as quota,
               COUNT(CASE WHEN b.status IN ('confirmed','completed') THEN 1 END) as used,
               COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
               COUNT(CASE WHEN b.status='cancelled' THEN 1 END) as cancelled,
               COUNT(b.id) as total_bookings,
               COALESCE(AVG(CASE WHEN b.rating THEN b.rating END), 0) as avg_given,
               COUNT(CASE WHEN b.rating THEN 1 END) as given_rating,
               MAX(b.date) as last_booking
        FROM users u
        LEFT JOIN bookings b ON b.user_id = u.id
        WHERE u.role = 'user'
        GROUP BY u.id
        ORDER BY completed DESC
    ''').fetchall()
    conn.close()

    return render_template('admin_member_records.html', members=members)

# ── 学员详细上课记录 ──────────────────────────────────────────
@app.route('/admin/member/<int:uid>/records')
def admin_member_detail(uid):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = db()
    member = conn.execute('SELECT * FROM users WHERE id=? AND role="user"', (uid,)).fetchone()
    bookings = conn.execute('''
        SELECT b.*, u.name as coach_name, c.specialty
        FROM bookings b
        JOIN coaches c ON b.coach_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE b.user_id = ?
        ORDER BY b.date DESC, b.time_slot DESC
    ''', (uid,)).fetchall()

    # 按月统计
    monthly = {}
    for b in bookings:
        ym = b['date'][:7]
        if ym not in monthly:
            monthly[ym] = {'total':0,'completed':0,'cancelled':0}
        monthly[ym]['total'] += 1
        if b['status'] == 'completed': monthly[ym]['completed'] += 1
        if b['status'] == 'cancelled': monthly[ym]['cancelled'] += 1

    conn.close()
    return render_template('admin_member_detail.html',
                           member=member,
                           bookings=bookings,
                           monthly=sorted(monthly.items(), reverse=True))

# ── 经营大屏 ──────────────────────────────────────────────────
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    today = datetime.now().strftime('%Y-%m-%d')
    this_month = datetime.now().strftime('%Y-%m')
    this_year = datetime.now().year

    conn = db()

    # 今日数据
    today_bookings = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE date=?", (today,)).fetchone()[0]
    today_completed = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE date=? AND status='completed'", (today,)).fetchone()[0]
    today_pending = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE date=? AND status='pending'", (today,)).fetchone()[0]

    # 累计数据
    total_members = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0]
    total_coaches = conn.execute(
        "SELECT COUNT(*) FROM coaches").fetchone()[0]
    total_bookings = conn.execute(
        "SELECT COUNT(*) FROM bookings").fetchone()[0]
    total_completed = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE status='completed'").fetchone()[0]

    # 本月数据
    month_start = this_month + '-01'
    month_bookings = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE date >= ?", (month_start,)).fetchone()[0]
    month_completed = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE date >= ? AND status='completed'", (month_start,)).fetchone()[0]

    # 今日预约详情
    today_list = conn.execute('''
        SELECT b.*, u.name as user_name, c2.name as coach_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN coaches c2 ON b.coach_id = c2.id
        WHERE b.date = ?
        ORDER BY b.time_slot
    ''', (today,)).fetchall()

    # 最近7天预约趋势
    week_data = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i))
        ds = d.strftime('%Y-%m-%d')
        cnt = conn.execute("SELECT COUNT(*) FROM bookings WHERE date=?", (ds,)).fetchone()[0]
        comp = conn.execute("SELECT COUNT(*) FROM bookings WHERE date=? AND status='completed'", (ds,)).fetchone()[0]
        week_data.append({
            'date': d.strftime('%m-%d'),
            'weekday': ['一','二','三','四','五','六','日'][d.weekday()],
            'bookings': cnt,
            'completed': comp
        })

    # 教练排名（本月）
    coach_ranking = conn.execute('''
        SELECT u.name as coach_name, c.id,
               COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
               COALESCE(AVG(CASE WHEN b.rating THEN b.rating END), 0) as avg_rating
        FROM coaches c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ?
        GROUP BY c.id
        ORDER BY completed DESC
        LIMIT 5
    ''', (month_start,)).fetchall()

    # 近期动态（最新20条）
    recent = conn.execute('''
        SELECT b.*, u.name as user_name, c2.name as coach_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN coaches c2 ON b.coach_id = c2.id
        ORDER BY b.created_at DESC
        LIMIT 20
    ''').fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
                         today=today,
                         today_bookings=today_bookings,
                         today_completed=today_completed,
                         today_pending=today_pending,
                         total_members=total_members,
                         total_coaches=total_coaches,
                         total_bookings=total_bookings,
                         total_completed=total_completed,
                         month_bookings=month_bookings,
                         month_completed=month_completed,
                         week_data=week_data,
                         coach_ranking=coach_ranking,
                         recent=recent)

# ── 月报导出 ──────────────────────────────────────────────────
@app.route('/admin/report/export')
def admin_export_report():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    year, mon = map(int, month.split('-'))
    start = f"{year}-{mon:02d}-01"
    if mon == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{mon+1:02d}-01"

    conn = db()

    # 1. 预约汇总
    bookings = conn.execute('''
        SELECT b.date, b.time_slot, b.status, b.rating, b.review,
               u.name as member_name, u.phone,
               c2.name as coach_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN coaches c2 ON b.coach_id = c2.id
        WHERE b.date >= ? AND b.date < ?
        ORDER BY b.date, b.time_slot
    ''', (start, end)).fetchall()

    # 2. 教练统计
    coaches = conn.execute('''
        SELECT u.name as coach_name,
               COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
               COUNT(CASE WHEN b.status IN ('confirmed','pending') THEN 1 END) as upcoming,
               COUNT(CASE WHEN b.status IN ('cancelled','rejected') THEN 1 END) as cancelled,
               COUNT(b.id) as total,
               COALESCE(AVG(CASE WHEN b.rating THEN b.rating END), 0) as avg_rating
        FROM coaches c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ? AND b.date < ?
        GROUP BY c.id
    ''', (start, end)).fetchall()

    # 3. 学员统计
    members = conn.execute('''
        SELECT u.name as member_name, u.phone,
               COUNT(CASE WHEN b.status IN ('confirmed','completed') THEN 1 END) as used,
               COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
               COUNT(CASE WHEN b.status='cancelled' THEN 1 END) as cancelled
        FROM users u
        LEFT JOIN bookings b ON b.user_id = u.id AND b.date >= ? AND b.date < ?
        WHERE u.role = 'user'
        GROUP BY u.id
        ORDER BY completed DESC
    ''', (start, end)).fetchall()

    conn.close()

    # 生成CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 月报标题
    writer.writerow([f'{month} 健身房月报'])
    writer.writerow([])

    # 教练统计
    writer.writerow(['【教练课时统计】'])
    writer.writerow(['教练姓名', '完成课时', '待上课时', '取消课时', '总预约', '平均评分'])
    for c in coaches:
        writer.writerow([
            c['coach_name'], c['completed'], c['upcoming'],
            c['cancelled'], c['total'], round(c['avg_rating'], 1)
        ])
    writer.writerow([])

    # 学员统计
    writer.writerow(['【学员上课统计】'])
    writer.writerow(['学员姓名', '手机号', '已用课时', '完成课时', '取消次数'])
    for m in members:
        writer.writerow([
            m['member_name'], m['phone'] or '-',
            m['used'], m['completed'], m['cancelled']
        ])
    writer.writerow([])

    # 预约明细
    writer.writerow([f"【{month} 预约明细】"])
    writer.writerow(['日期', '时间', '学员', '教练', '状态', '评分', '评价'])
    for b in bookings:
        status_map = {
            'pending': '待确认', 'confirmed': '已确认',
            'completed': '已完成', 'cancelled': '已取消', 'rejected': '已拒绝'
        }
        writer.writerow([
            b['date'], b['time_slot'], b['member_name'], b['coach_name'],
            status_map.get(b['status'], b['status']),
            b['rating'] or '-', b['review'] or '-'
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=gym_report_{month}.csv',
            'Content-Type': 'text/csv; charset=utf-8-sig'
        }
    )
