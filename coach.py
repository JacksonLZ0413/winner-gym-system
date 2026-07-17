# -*- coding: utf-8 -*-
from flask import render_template, request, redirect, url_for, session, flash
from datetime import datetime
from auth import get_db, validate_csrf

# ── 教练后台 ────────────────────────────────────────────────────
def init_coach_routes(app):
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
        bookings = conn.execute('''
            SELECT b.*, u.name, u.phone, co.name as course_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            LEFT JOIN courses co ON b.course_id = co.id
            WHERE b.coach_id = ? AND b.date >= ?
            ORDER BY b.date, b.time_slot
        ''', (coach['id'], today)).fetchall()

        reviews = conn.execute('''
            SELECT b.rating, b.review, b.created_at, u.name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.coach_id = ? AND b.rating IS NOT NULL
            ORDER BY b.created_at DESC LIMIT 10
        ''', (coach['id'],)).fetchall()

        # 排班
        schedule = conn.execute('''
            SELECT weekday, start_time, end_time FROM time_slots
            WHERE coach_id = ? ORDER BY weekday, start_time
        ''', (coach['id'],)).fetchall()

        conn.close()
        return render_template('coach_dashboard.html', coach=coach,
                              bookings=bookings, reviews=reviews, schedule=schedule)

    @app.route('/coach/respond', methods=['POST'])
    def coach_respond():
        if 'user_id' not in session or session.get('role') != 'coach':
            return redirect(url_for('login'))
        if validate_csrf():
            return redirect(url_for('coach_dashboard'))

        bid   = request.form.get('booking_id')
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

    @app.route('/coach/schedule', methods=['POST'])
    def coach_update_schedule():
        if 'user_id' not in session or session.get('role') != 'coach':
            return redirect(url_for('login'))
        if validate_csrf():
            return redirect(url_for('coach_dashboard'))

        conn = get_db()
        coach = conn.execute('SELECT id FROM coaches WHERE user_id=?', (session['user_id'],)).fetchone()
        coach_id = coach['id']

        conn.execute('DELETE FROM time_slots WHERE coach_id=?', (coach_id,))

        weekdays = request.form.getlist('weekday')
        starts   = request.form.getlist('start_time')
        ends     = request.form.getlist('end_time')

        for i in range(len(weekdays)):
            w = weekdays[i]
            s = starts[i]
            e = ends[i]
            if w and s and e:
                conn.execute(
                    'INSERT INTO time_slots (coach_id, weekday, start_time, end_time) VALUES (?, ?, ?, ?)',
                    (coach_id, int(w), s, e)
                )

        conn.commit()
        conn.close()
        flash('排班已更新', 'success')
        return redirect(url_for('coach_dashboard'))
