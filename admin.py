# -*- coding: utf-8 -*-
from flask import render_template, request, redirect, url_for, session, flash, Response, jsonify
from datetime import datetime
import io, csv
import sqlite3
from auth import get_db, validate_csrf, hash_password, escape

# ── 管理员后台 ──────────────────────────────────────────────────
def init_admin_routes(app):
    @app.route('/admin')
    def admin():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        conn = get_db()
        stats = {
            'total_users':  conn.execute('SELECT COUNT(*) FROM users WHERE role="user"').fetchone()[0],
            'total_coaches': conn.execute('SELECT COUNT(*) FROM coaches').fetchone()[0],
            'total_bookings': conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],
            'pending_bookings': conn.execute("SELECT COUNT(*) FROM bookings WHERE status='pending'").fetchone()[0],
        }
        recent = conn.execute('''
            SELECT b.*, u.name as user_name, u2.name as coach_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN coaches c ON b.coach_id = c.id
            JOIN users u2 ON c.user_id = u2.id
            ORDER BY b.created_at DESC LIMIT 20
        ''').fetchall()
        conn.close()
        return render_template('admin.html', stats=stats, recent_bookings=recent)

    @app.route('/admin/users')
    def admin_users():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        conn = get_db()
        users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
        conn.close()
        return render_template('admin_users.html', users=users)

    @app.route('/admin/user/password/reset/<int:user_id>')
    def admin_reset_password_page(user_id):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        conn.close()
        if not user:
            flash('用户不存在', 'error')
            return redirect(url_for('admin_users'))
        return render_template('admin_reset_password.html', user=user)

    @app.route('/admin/user/password', methods=['POST'])
    def admin_change_user_password():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        uid   = request.form.get('user_id')
        pwd   = request.form.get('new_password', '')
        if len(pwd) < 6:
            flash('密码至少6位', 'error')
            return redirect(url_for('admin_reset_password_page', user_id=uid))
        else:
            conn = get_db()
            conn.execute('UPDATE users SET password=? WHERE id=?', (hash_password(pwd), uid))
            conn.commit()
            conn.close()
            flash('密码已修改', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/coaches')
    def admin_coaches():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        conn = get_db()
        coaches = conn.execute('''
            SELECT c.*, u.name, u.username, u.avatar
            FROM coaches c JOIN users u ON c.user_id = u.id
        ''').fetchall()
        conn.close()
        return render_template('admin_coaches.html', coaches=coaches)

    @app.route('/admin/coaches/add/page')
    def admin_add_coach_page():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        return render_template('admin_add_coach.html')

    @app.route('/admin/coaches/add', methods=['POST'])
    def admin_add_coach():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        username   = escape(request.form.get('username', '').strip())
        password   = request.form.get('password', '')
        name       = escape(request.form.get('name', '').strip())
        bio        = escape(request.form.get('bio', '').strip())
        specialty  = escape(request.form.get('specialty', '').strip())
        experience = request.form.get('experience', '1')

        if not username or not password or not name:
            flash('用户名、密码、姓名为必填项', 'error')
            return redirect(url_for('admin_add_coach_page'))

        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password, role, name) VALUES (?, ?, ?, ?)',
                        (username, hash_password(password), 'coach', name))
            user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.execute('''
                INSERT INTO coaches (user_id, bio, specialty, experience, rating, rating_count)
                VALUES (?, ?, ?, ?, 5.0, 0)
            ''', (user_id, bio, specialty, int(experience)))
            cid = conn.execute('SELECT id FROM coaches WHERE user_id=?', (user_id,)).fetchone()[0]
            for wd in range(1, 6):
                for s, e in [('09:00','12:00'),('14:00','18:00'),('19:00','21:00')]:
                    conn.execute(
                        'INSERT INTO time_slots (coach_id, weekday, start_time, end_time) VALUES (?,?,?,?)',
                        (cid, wd, s, e))
            conn.commit()
            flash(f'教练 {name} 添加成功', 'success')
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('用户名已存在', 'error')
        finally:
            conn.close()
        return redirect(url_for('admin_coaches'))

    @app.route('/admin/coaches/delete/<int:coach_id>', methods=['POST'])
    def admin_delete_coach(coach_id):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        conn = get_db()
        coach = conn.execute('SELECT user_id FROM coaches WHERE id=?', (coach_id,)).fetchone()
        if coach:
            uid = coach['user_id']
            conn.execute('DELETE FROM time_slots WHERE coach_id=?', (coach_id,))
            conn.execute("UPDATE bookings SET status='cancelled' WHERE coach_id=?", (coach_id,))
            conn.execute('DELETE FROM coaches WHERE id=?', (coach_id,))
            conn.execute('DELETE FROM users WHERE id=?', (uid,))
            conn.commit()
            flash('教练已删除', 'success')
        conn.close()
        return redirect(url_for('admin_coaches'))

    @app.route('/admin/coaches/edit/<int:coach_id>')
    def admin_edit_coach_page(coach_id):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        conn = get_db()
        coach = conn.execute('''
            SELECT c.*, u.name, u.username
            FROM coaches c JOIN users u ON c.user_id = u.id
            WHERE c.id=?
        ''', (coach_id,)).fetchone()
        conn.close()
        if not coach:
            flash('教练不存在', 'error')
            return redirect(url_for('admin_coaches'))
        return render_template('admin_edit_coach.html', coach=coach)

    @app.route('/admin/coaches/edit', methods=['POST'])
    def admin_edit_coach():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        coach_id = request.form.get('coach_id')
        user_id = request.form.get('user_id')
        name = escape(request.form.get('name', '').strip())
        username = escape(request.form.get('username', '').strip())
        password = request.form.get('password', '')
        specialty = escape(request.form.get('specialty', '').strip())
        experience = request.form.get('experience', '1')
        bio = escape(request.form.get('bio', '').strip())

        if not name or not username:
            flash('姓名和用户名为必填项', 'error')
            return redirect(url_for('admin_edit_coach_page', coach_id=coach_id))

        conn = get_db()
        try:
            if password:
                conn.execute('UPDATE users SET password=? WHERE id=?', (hash_password(password), user_id))
            conn.execute('UPDATE users SET name=?, username=? WHERE id=?', (name, username, user_id))
            conn.execute('UPDATE coaches SET bio=?, specialty=?, experience=? WHERE id=?', (bio, specialty, int(experience), coach_id))
            conn.commit()
            flash('教练信息已更新', 'success')
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('用户名已存在', 'error')
        finally:
            conn.close()
        return redirect(url_for('admin_coaches'))

    @app.route('/admin/users/courses')
    def admin_user_courses():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        keyword = request.args.get('keyword', '').strip()
        
        conn = get_db()
        if keyword:
            users = conn.execute('''
                SELECT u.id, u.name, u.username, u.phone,
                       COALESCE(u.course_quota,0) AS course_quota,
                       COUNT(CASE WHEN b.status IN ('confirmed','completed') THEN 1 END) AS used
                FROM users u
                LEFT JOIN bookings b ON b.user_id = u.id
                WHERE u.role='user' AND (u.name LIKE ? OR u.phone LIKE ?)
                GROUP BY u.id ORDER BY u.created_at DESC
            ''', ('%' + keyword + '%', '%' + keyword + '%')).fetchall()
        else:
            users = conn.execute('''
                SELECT u.id, u.name, u.username, u.phone,
                       COALESCE(u.course_quota,0) AS course_quota,
                       COUNT(CASE WHEN b.status IN ('confirmed','completed') THEN 1 END) AS used
                FROM users u
                LEFT JOIN bookings b ON b.user_id = u.id
                WHERE u.role='user'
                GROUP BY u.id ORDER BY u.created_at DESC
            ''').fetchall()
        conn.close()
        return render_template('admin_user_courses.html', users=users, keyword=keyword)

    @app.route('/admin/users/courses/update/<int:user_id>')
    def admin_update_course_quota_page(user_id):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=? AND role="user"', (user_id,)).fetchone()
        conn.close()
        if not user:
            flash('用户不存在', 'error')
            return redirect(url_for('admin_user_courses'))
        return render_template('admin_update_quota.html', user=user)

    @app.route('/admin/users/courses/update', methods=['POST'])
    def admin_update_course_quota():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        uid   = request.form.get('user_id')
        quota = max(0, int(request.form.get('quota', 0) or 0))

        conn = get_db()
        conn.execute('UPDATE users SET course_quota=? WHERE id=?', (quota, uid))
        conn.commit()
        conn.close()
        flash('课程配额已更新', 'success')
        return redirect(url_for('admin_user_courses'))

    # ── 教练课时统计 ────────────────────────────────────────────────
    @app.route('/admin/stats/coaches')
    def admin_coach_stats():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        year, mon = map(int, month.split('-'))
        start = f"{year}-{mon:02d}-01"
        end = f"{year+1}-01-01" if mon == 12 else f"{year}-{mon+1:02d}-01"
        conn = get_db()
        
        import datetime as dt
        today = dt.datetime.now()
        months = []
        for i in range(12):
            date = today - dt.timedelta(days=i*30)
            months.append(date.strftime('%Y-%m'))
        months = list(set(months))
        months.sort(reverse=True)
        
        coaches = conn.execute('''
            SELECT c.id, u.name,
                   COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                   COUNT(CASE WHEN b.status='confirmed' THEN 1 END) as confirmed,
                   COUNT(CASE WHEN b.status='pending' THEN 1 END) as pending,
                   COUNT(CASE WHEN b.status IN ('cancelled','rejected') THEN 1 END) as cancelled,
                   COUNT(b.id) as total
            FROM coaches c JOIN users u ON c.user_id = u.id
            LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ? AND b.date < ?
            GROUP BY c.id ORDER BY completed DESC
        ''', (start, end)).fetchall()
        
        coaches_list = []
        for c in coaches:
            coach_dict = {
                'id': c[0],
                'name': c[1],
                'completed': c[2],
                'confirmed': c[3],
                'pending': c[4],
                'cancelled': c[5],
                'total': c[6]
            }
            avg_rating_result = conn.execute('''
                SELECT AVG(rating)
                FROM bookings
                WHERE coach_id=? AND status='completed' AND rating IS NOT NULL AND date >= ? AND date < ?
            ''', (coach_dict['id'], start, end)).fetchone()
            avg_rating = avg_rating_result[0] if (avg_rating_result and avg_rating_result[0] is not None) else 0
            coach_dict['avg_rating'] = avg_rating
            coaches_list.append(coach_dict)
        
        total_completed = sum(c['completed'] for c in coaches_list)
        total_confirmed = sum(c['confirmed'] for c in coaches_list)
        total_cancelled = sum(c['cancelled'] for c in coaches_list)
        
        conn.close()
        return render_template('admin_coach_stats.html', 
                           coaches=coaches_list, 
                           month=month, 
                           months=months,
                           total_completed=total_completed,
                           total_confirmed=total_confirmed,
                           total_cancelled=total_cancelled)


    # ── 学员详情与记录 ────────────────────────────────────────────
    @app.route('/admin/member/<int:member_id>/records')
    def admin_member_detail(member_id):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        conn = get_db()
        member = conn.execute('SELECT * FROM users WHERE id=? AND role="user"', (member_id,)).fetchone()
        if not member:
            flash('学员不存在', 'error')
            return redirect(url_for('admin_member_records'))
        
        bookings = conn.execute('''
            SELECT b.*, u.name as coach_name, c.specialty
            FROM bookings b
            JOIN coaches c ON b.coach_id = c.id
            JOIN users u ON c.user_id = u.id
            WHERE b.user_id=?
            ORDER BY b.date DESC, b.time_slot DESC
        ''', (member_id,)).fetchall()
        
        monthly_stats = conn.execute('''
            SELECT strftime('%Y-%m', b.date) as month,
                   COUNT(*) as total,
                   COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                   COUNT(CASE WHEN b.status='cancelled' THEN 1 END) as cancelled
            FROM bookings b
            WHERE b.user_id=? AND b.date IS NOT NULL
            GROUP BY month
            ORDER BY month DESC
        ''', (member_id,)).fetchall()
        
        monthly = []
        for m in monthly_stats:
            monthly.append((m['month'], {'total': m['total'], 'completed': m['completed'], 'cancelled': m['cancelled']}))
        
        conn.close()
        return render_template('admin_member_detail.html', member=member, bookings=bookings, monthly=monthly)

    # ── 学员上课记录汇总 ────────────────────────────────────────────
    @app.route('/admin/member_records')
    def admin_member_records():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        
        keyword = request.args.get('keyword', '').strip()
        
        conn = get_db()
        if keyword:
            members = conn.execute('''
                SELECT u.id, u.name, u.phone, COALESCE(u.course_quota,0) as quota,
                       COUNT(CASE WHEN b.status IN ('confirmed','completed') THEN 1 END) as used,
                       COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                       MAX(b.date) as last_booking
                FROM users u LEFT JOIN bookings b ON b.user_id = u.id
                WHERE u.role = 'user' AND (u.name LIKE ? OR u.phone LIKE ?)
                GROUP BY u.id ORDER BY completed DESC
            ''', ('%' + keyword + '%', '%' + keyword + '%')).fetchall()
        else:
            members = conn.execute('''
                SELECT u.id, u.name, u.phone, COALESCE(u.course_quota,0) as quota,
                       COUNT(CASE WHEN b.status IN ('confirmed','completed') THEN 1 END) as used,
                       COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                       MAX(b.date) as last_booking
                FROM users u LEFT JOIN bookings b ON b.user_id = u.id
                WHERE u.role = 'user' GROUP BY u.id ORDER BY completed DESC
            ''').fetchall()
        conn.close()
        return render_template('admin_member_records.html', members=members, keyword=keyword)

    # ── 经营大屏 ────────────────────────────────────────────────────
    @app.route('/admin/dashboard')
    def admin_dashboard():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        time_range = request.args.get('range', 'week')
        today = datetime.now().strftime('%Y-%m-%d')
        month_start = datetime.now().strftime('%Y-%m') + '-01'

        import datetime as dt
        today_dt = dt.datetime.now()
        week_start = (today_dt - dt.timedelta(days=today_dt.weekday())).strftime('%Y-%m-%d')

        conn = get_db()

        today_stats = {
            'today_bookings': conn.execute("SELECT COUNT(*) FROM bookings WHERE date=?", (today,)).fetchone()[0],
            'today_pending': conn.execute("SELECT COUNT(*) FROM bookings WHERE date=? AND status='pending'", (today,)).fetchone()[0],
            'today_completed': conn.execute("SELECT COUNT(*) FROM bookings WHERE date=? AND status='completed'", (today,)).fetchone()[0],
            'today_active_members': conn.execute("SELECT COUNT(DISTINCT user_id) FROM bookings WHERE date=?", (today,)).fetchone()[0],
        }

        month_stats = {
            'total_bookings': conn.execute("SELECT COUNT(*) FROM bookings WHERE date>=?", (month_start,)).fetchone()[0],
            'completed_bookings': conn.execute("SELECT COUNT(*) FROM bookings WHERE date>=? AND status='completed'", (month_start,)).fetchone()[0],
            'new_members': conn.execute("SELECT COUNT(*) FROM users WHERE role='user' AND created_at>=?", (month_start,)).fetchone()[0],
            'avg_rating': conn.execute("SELECT AVG(rating) FROM bookings WHERE date>=? AND status='completed' AND rating IS NOT NULL", (month_start,)).fetchone()[0] or 0,
        }
        month_stats['completion_rate'] = round((month_stats['completed_bookings'] / month_stats['total_bookings'] * 100), 1) if month_stats['total_bookings'] > 0 else 0

        total_stats = {
            'total_members': conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
            'total_coaches': conn.execute("SELECT COUNT(*) FROM coaches").fetchone()[0],
            'total_completed': conn.execute("SELECT COUNT(*) FROM bookings WHERE status='completed'").fetchone()[0],
            'total_bookings': conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        }

        week_data = []
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        for i in range(7):
            date = (dt.datetime.now() - dt.timedelta(days=6-i)).strftime('%Y-%m-%d')
            bookings = conn.execute("SELECT COUNT(*) FROM bookings WHERE date=?", (date,)).fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM bookings WHERE date=? AND status='completed'", (date,)).fetchone()[0]
            week_data.append({
                'date': date,
                'weekday': weekdays[i],
                'bookings': bookings,
                'completed': completed
            })

        coach_stats = conn.execute('''
            SELECT u.name as coach_name,
                   COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                   COUNT(b.id) as total,
                   AVG(CASE WHEN b.status='completed' AND b.rating IS NOT NULL THEN b.rating END) as avg_rating
            FROM coaches c JOIN users u ON c.user_id = u.id
            LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ?
            GROUP BY c.id ORDER BY completed DESC LIMIT 10
        ''', (month_start,)).fetchall()

        coach_ranking = []
        for coach in coach_stats:
            booking_rate = round((coach['completed'] / coach['total'] * 100), 1) if coach['total'] > 0 else 0
            coach_ranking.append({
                'coach_name': coach['coach_name'],
                'completed': coach['completed'],
                'total': coach['total'],
                'booking_rate': booking_rate,
                'avg_rating': coach['avg_rating'] or 0
            })

        pending_bookings = conn.execute('''
            SELECT b.*, u.name as user_name, u2.name as coach_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN coaches c ON b.coach_id = c.id
            JOIN users u2 ON c.user_id = u2.id
            WHERE b.status='pending'
            ORDER BY b.created_at DESC LIMIT 10
        ''').fetchall()

        today_schedule = conn.execute('''
            SELECT b.*, u.name as user_name, u2.name as coach_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN coaches c ON b.coach_id = c.id
            JOIN users u2 ON c.user_id = u2.id
            WHERE b.date=?
            ORDER BY b.time_slot
        ''', (today,)).fetchall()

        recent = conn.execute('''
            SELECT b.*, u.name as user_name, u2.name as coach_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN coaches c2 ON b.coach_id = c2.id
            JOIN users u2 ON c2.user_id = u2.id
            ORDER BY b.created_at DESC LIMIT 20
        ''').fetchall()

        conn.close()

        chart_data = {
            'booking_trend': {
                'labels': [d['weekday'] for d in week_data],
                'bookings': [d['bookings'] for d in week_data],
                'completed': [d['completed'] for d in week_data]
            },
            'coach_performance': {
                'coaches': [c['coach_name'] for c in coach_ranking[:5]],
                'hours': [c['completed'] for c in coach_ranking[:5]],
                'booking_rate': [c['booking_rate'] for c in coach_ranking[:5]]
            }
        }

        import json
        chart_data_json = json.dumps(chart_data)

        return render_template('admin_dashboard.html',
                           today=today,
                           today_stats=today_stats,
                           month_stats=month_stats,
                           total_stats=total_stats,
                           week_data=week_data,
                           coach_ranking=coach_ranking,
                           pending_bookings=pending_bookings,
                           today_schedule=today_schedule,
                           recent=recent,
                           chart_data=chart_data_json)

    @app.route('/admin/dashboard/chart_data')
    def admin_dashboard_chart_data():
        if 'user_id' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 401

        time_range = request.args.get('range', 'week')
        today = datetime.now().strftime('%Y-%m-%d')

        import datetime as dt
        today_dt = dt.datetime.now()

        conn = get_db()

        if time_range == 'today':
            hours = ['{:02d}:00'.format(i) for i in range(9, 22)]
            labels = hours
            data_bookings = []
            data_completed = []
            for hour in hours:
                bookings = conn.execute("""
                    SELECT COUNT(*) FROM bookings
                    WHERE date=? AND time_slot LIKE ?
                """, (today, hour + '%')).fetchone()[0]
                completed = conn.execute("""
                    SELECT COUNT(*) FROM bookings
                    WHERE date=? AND time_slot LIKE ? AND status='completed'
                """, (today, hour + '%')).fetchone()[0]
                data_bookings.append(bookings)
                data_completed.append(completed)

            coach_stats = conn.execute('''
                SELECT u.name as coach_name,
                       COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                       COUNT(b.id) as total
                FROM coaches c JOIN users u ON c.user_id = u.id
                LEFT JOIN bookings b ON b.coach_id = c.id AND b.date = ?
                GROUP BY c.id ORDER BY completed DESC LIMIT 5
            ''', (today,)).fetchall()

        elif time_range == 'week':
            weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            labels = weekdays
            data_bookings = []
            data_completed = []
            for i in range(7):
                date = (today_dt - dt.timedelta(days=6-i)).strftime('%Y-%m-%d')
                bookings = conn.execute("SELECT COUNT(*) FROM bookings WHERE date=?", (date,)).fetchone()[0]
                completed = conn.execute("SELECT COUNT(*) FROM bookings WHERE date=? AND status='completed'", (date,)).fetchone()[0]
                data_bookings.append(bookings)
                data_completed.append(completed)

            month_start = datetime.now().strftime('%Y-%m') + '-01'
            coach_stats = conn.execute('''
                SELECT u.name as coach_name,
                       COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                       COUNT(b.id) as total
                FROM coaches c JOIN users u ON c.user_id = u.id
                LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ?
                GROUP BY c.id ORDER BY completed DESC LIMIT 5
            ''', (month_start,)).fetchall()

        else:
            days_in_month = (today_dt.replace(day=1) - dt.timedelta(days=1)).day if today_dt.month == 1 else (today_dt.replace(month=today_dt.month+1, day=1) - dt.timedelta(days=1)).day
            month_start = datetime.now().strftime('%Y-%m') + '-01'
            labels = ['{:02d}日'.format(i) for i in range(1, days_in_month + 1)]
            data_bookings = []
            data_completed = []
            for i in range(1, days_in_month + 1):
                date = datetime.now().strftime('%Y-%m') + '-{:02d}'.format(i)
                if date > today:
                    data_bookings.append(0)
                    data_completed.append(0)
                else:
                    bookings = conn.execute("SELECT COUNT(*) FROM bookings WHERE date=?", (date,)).fetchone()[0]
                    completed = conn.execute("SELECT COUNT(*) FROM bookings WHERE date=? AND status='completed'", (date,)).fetchone()[0]
                    data_bookings.append(bookings)
                    data_completed.append(completed)

            coach_stats = conn.execute('''
                SELECT u.name as coach_name,
                       COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                       COUNT(b.id) as total
                FROM coaches c JOIN users u ON c.user_id = u.id
                LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ?
                GROUP BY c.id ORDER BY completed DESC LIMIT 5
            ''', (month_start,)).fetchall()

        coach_ranking = []
        for coach in coach_stats:
            booking_rate = round((coach['completed'] / coach['total'] * 100), 1) if coach['total'] > 0 else 0
            coach_ranking.append({
                'coach_name': coach['coach_name'],
                'completed': coach['completed'],
                'total': coach['total'],
                'booking_rate': booking_rate
            })

        conn.close()

        result = {
            'booking_trend': {
                'labels': labels,
                'bookings': data_bookings,
                'completed': data_completed
            },
            'coach_performance': {
                'coaches': [c['coach_name'] for c in coach_ranking],
                'hours': [c['completed'] for c in coach_ranking],
                'booking_rate': [c['booking_rate'] for c in coach_ranking]
            }
        }

        return jsonify(result)

    # ── 月报导出 CSV ────────────────────────────────────────────────
    @app.route('/admin/report/export')
    def admin_export_report():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        year, mon = map(int, month.split('-'))
        start = f"{year}-{mon:02d}-01"
        end = f"{year+1}-01-01" if mon == 12 else f"{year}-{mon+1:02d}-01"
        conn = get_db()
        bookings = conn.execute('''
            SELECT b.date, b.time_slot, b.status, b.rating,
                   u.name as member, c2.name as coach
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN coaches c2 ON b.coach_id = c2.id
            WHERE b.date >= ? AND b.date < ?
            ORDER BY b.date, b.time_slot
        ''', (start, end)).fetchall()
        coaches = conn.execute('''
            SELECT u.name as coach_name,
                   COUNT(CASE WHEN b.status='completed' THEN 1 END) as completed,
                   COUNT(CASE WHEN b.status IN ('cancelled','rejected') THEN 1 END) as cancelled,
                   COUNT(b.id) as total
            FROM coaches c JOIN users u ON c.user_id = u.id
            LEFT JOIN bookings b ON b.coach_id = c.id AND b.date >= ? AND b.date < ?
            GROUP BY c.id ORDER BY completed DESC
        ''', (start, end)).fetchall()
        conn.close()
        import io, csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([f'{month} 健身房运营月报'])
        writer.writerow([])
        writer.writerow(['教练课时统计'])
        writer.writerow(['教练', '完成', '取消', '总计'])
        for c in coaches:
            writer.writerow([c['coach_name'], c['completed'], c['cancelled'], c['total']])
        writer.writerow([])
        writer.writerow(['预约明细'])
        writer.writerow(['日期', '时间', '学员', '教练', '状态', '评分'])
        for b in bookings:
            writer.writerow([b['date'], b['time_slot'], b['member'], b['coach'], b['status'], b['rating'] or '-'])
        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename=gym_report_{month}.csv'})
