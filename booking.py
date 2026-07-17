# -*- coding: utf-8 -*-
from flask import render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from auth import get_db, escape, validate_csrf

# ── 教练列表 ────────────────────────────────────────────────────
def init_booking_routes(app):
    @app.route('/coaches')
    def coaches():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn = get_db()
        coaches = conn.execute('''
            SELECT c.*, u.name, u.avatar
            FROM coaches c
            JOIN users u ON c.user_id = u.id
        ''').fetchall()
        conn.close()
        return render_template('coaches.html', coaches=coaches)

    # ── 教练详情 & 预约 ──────────────────────────────────────────────
    @app.route('/coach/<int:coach_id>', methods=['GET', 'POST'])
    def coach_detail(coach_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn = get_db()
        coach = conn.execute('''
            SELECT c.*, u.name, u.avatar
            FROM coaches c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
        ''', (coach_id,)).fetchone()

        if not coach:
            conn.close()
            flash('教练不存在', 'error')
            return redirect(url_for('coaches'))

        # 获取教练可教授的课程
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
                    all_slots.append({'date': date_str, 'time': ts, 'booked': (date_str, ts) in booked})
        conn.close()

        return render_template('coach.html', coach=coach, reviews=reviews,
                              week_dates=week_dates, all_time_slots=all_slots, courses=courses)

    # ── 预约课程 ────────────────────────────────────────────────────
    @app.route('/book', methods=['POST'])
    def book():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if validate_csrf():
            return redirect(url_for('my_bookings'))

        coach_id = request.form.get('coach_id')
        course_id = request.form.get('course_id')
        date     = request.form.get('date')
        time_slot = request.form.get('time_slot')
        note     = escape(request.form.get('note', '').strip())

        if not date or not time_slot or not coach_id or not course_id:
            flash('请选择课程、日期和时间段', 'error')
            return redirect(url_for('coach_detail', coach_id=coach_id))

        conn = get_db()

        # 检查课程配额
        user = conn.execute('SELECT course_quota FROM users WHERE id=?', (session['user_id'],)).fetchone()
        quota = user['course_quota'] or 0
        used  = conn.execute("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status IN ('confirmed','completed')", (session['user_id'],)).fetchone()[0]

        if quota > 0 and used >= quota:
            conn.close()
            flash('您的课程配额已用完，请联系管理员增加配额', 'error')
            return redirect(url_for('my_bookings'))

        # 检查重复预约
        exist = conn.execute('''
            SELECT id FROM bookings WHERE coach_id=? AND date=? AND time_slot=?
            AND status NOT IN ('cancelled','rejected')
        ''', (coach_id, date, time_slot)).fetchone()

        if exist:
            conn.close()
            flash('该时间段已被预约', 'error')
            return redirect(url_for('coach_detail', coach_id=coach_id))

        conn.execute('''
            INSERT INTO bookings (user_id, coach_id, course_id, date, time_slot, note, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (session['user_id'], coach_id, course_id, date, time_slot, note))
        conn.commit()
        conn.close()

        flash('预约成功，等待教练确认', 'success')
        return redirect(url_for('my_bookings'))

    # ── 我的预约 ────────────────────────────────────────────────────
    @app.route('/my_bookings')
    def my_bookings():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn = get_db()
        user = conn.execute('SELECT course_quota FROM users WHERE id=?', (session['user_id'],)).fetchone()
        used = conn.execute("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status IN ('confirmed','completed')", (session['user_id'],)).fetchone()[0]
        quota = user['course_quota'] or 0
        remain = max(0, quota - used) if quota > 0 else '无限制'

        bookings = conn.execute('''
            SELECT b.*, c.specialty, u.name as coach_name, co.name as course_name
            FROM bookings b
            JOIN coaches c ON b.coach_id = c.id
            JOIN users u ON c.user_id = u.id
            LEFT JOIN courses co ON b.course_id = co.id
            WHERE b.user_id = ?
            ORDER BY b.date DESC, b.time_slot DESC
        ''', (session['user_id'],)).fetchall()
        conn.close()

        return render_template('my_bookings.html', bookings=bookings,
                              quota=quota, used=used, remain=remain)

    @app.route('/cancel_booking/<int:booking_id>')
    def cancel_booking(booking_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn = get_db()
        b = conn.execute('SELECT * FROM bookings WHERE id=? AND user_id=?',
                        (booking_id, session['user_id'])).fetchone()
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

        bid    = request.form.get('booking_id')
        rating = int(request.form.get('rating', 5))
        review = escape(request.form.get('review', '').strip())
        # 处理多个评价标签（复选框）
        review_tags = request.form.getlist('review_tags')
        review_tags = ','.join([escape(tag) for tag in review_tags])
        # 图片上传功能可以在这里添加，暂时留空
        review_images = ''

        conn = get_db()
        conn.execute('UPDATE bookings SET rating=?, review=?, review_tags=?, review_images=? WHERE id=? AND user_id=?',
                    (rating, review, review_tags, review_images, bid, session['user_id']))

        cid = conn.execute('SELECT coach_id FROM bookings WHERE id=?', (bid,)).fetchone()
        if cid:
            avg = conn.execute('SELECT AVG(rating) FROM bookings WHERE coach_id=? AND rating IS NOT NULL',
                              (cid[0],)).fetchone()[0]
            cnt = conn.execute('SELECT COUNT(*) FROM bookings WHERE coach_id=? AND rating IS NOT NULL',
                              (cid[0],)).fetchone()[0]
            conn.execute('UPDATE coaches SET rating=?, rating_count=? WHERE id=?',
                        (round(avg, 1), cnt, cid[0]))

        conn.commit()
        conn.close()
        flash('评价成功，感谢您的反馈！', 'success')
        return redirect(url_for('my_bookings'))
