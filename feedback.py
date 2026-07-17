# -*- coding: utf-8 -*-
from flask import render_template, request, redirect, url_for, session, flash
from auth import get_db, validate_csrf, escape

# ── 反馈功能 ────────────────────────────────────────────────────
def init_feedback_routes(app):
    @app.route('/feedback', methods=['GET', 'POST'])
    def feedback():
        if request.method == 'POST':
            if validate_csrf():
                return redirect(url_for('feedback'))

            name = escape(request.form.get('name', '').strip())
            email = escape(request.form.get('email', '').strip())
            phone = escape(request.form.get('phone', '').strip())
            subject = escape(request.form.get('subject', '').strip())
            content = escape(request.form.get('content', '').strip())

            if not name or not subject or not content:
                flash('姓名、主题和内容为必填项', 'error')
                return redirect(url_for('feedback'))

            conn = get_db()
            try:
                user_id = session.get('user_id') if 'user_id' in session else None
                conn.execute('''
                    INSERT INTO feedback (user_id, name, email, phone, subject, content, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending')
                ''', (user_id, name, email, phone, subject, content))
                conn.commit()
                flash('反馈提交成功，我们会尽快处理！', 'success')
                return redirect(url_for('feedback'))
            finally:
                conn.close()

        return render_template('feedback.html')

    @app.route('/admin/feedback')
    def admin_feedback():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        conn = get_db()
        feedbacks = conn.execute('''
            SELECT f.*, u.name as user_name
            FROM feedback f
            LEFT JOIN users u ON f.user_id = u.id
            ORDER BY f.created_at DESC
        ''').fetchall()
        conn.close()
        return render_template('admin_feedback.html', feedbacks=feedbacks)

    @app.route('/admin/feedback/status', methods=['POST'])
    def admin_update_feedback_status():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        if validate_csrf():
            return redirect(url_for('admin_feedback'))

        feedback_id = request.form.get('feedback_id')
        status = request.form.get('status')

        conn = get_db()
        conn.execute('UPDATE feedback SET status=? WHERE id=?', (status, feedback_id))
        conn.commit()
        conn.close()
        flash('反馈状态已更新', 'success')
        return redirect(url_for('admin_feedback'))
