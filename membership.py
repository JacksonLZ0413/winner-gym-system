# -*- coding: utf-8 -*-
from flask import render_template, request, redirect, url_for, session, flash
from auth import get_db, validate_csrf, escape

# ── 会员管理功能 ────────────────────────────────────────────────────
def init_membership_routes(app):
    @app.route('/membership')
    def membership():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
        
        # 获取会员等级信息
        level = conn.execute('SELECT * FROM membership_levels WHERE id=?', (user['level_id'],)).fetchone() if user['level_id'] else None
        
        # 获取积分记录
        points_history = conn.execute('''
            SELECT * FROM user_points 
            WHERE user_id=? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (session['user_id'],)).fetchall()
        
        # 获取所有会员等级信息
        all_levels = conn.execute('SELECT * FROM membership_levels ORDER BY min_points').fetchall()
        
        conn.close()
        return render_template('membership.html', user=user, level=level, points_history=points_history, all_levels=all_levels)

    @app.route('/admin/membership')
    def admin_membership():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))

        conn = get_db()
        users = conn.execute('''
            SELECT u.*, ml.name as level_name 
            FROM users u 
            LEFT JOIN membership_levels ml ON u.level_id = ml.id 
            WHERE u.role = 'user' 
            ORDER BY u.points DESC
        ''').fetchall()
        
        levels = conn.execute('SELECT * FROM membership_levels ORDER BY min_points').fetchall()
        conn.close()
        return render_template('admin_membership.html', users=users, levels=levels)

    @app.route('/admin/membership/level', methods=['POST'])
    def admin_update_level():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        if validate_csrf():
            return redirect(url_for('admin_membership'))

        user_id = request.form.get('user_id')
        level_id = request.form.get('level_id')

        conn = get_db()
        conn.execute('UPDATE users SET level_id=? WHERE id=?', (level_id, user_id))
        conn.commit()
        conn.close()
        flash('会员等级已更新', 'success')
        return redirect(url_for('admin_membership'))

    @app.route('/admin/membership/points', methods=['POST'])
    def admin_update_points():
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        if validate_csrf():
            return redirect(url_for('admin_membership'))

        user_id = request.form.get('user_id')
        points = int(request.form.get('points', 0))

        conn = get_db()
        conn.execute('UPDATE users SET points=? WHERE id=?', (points, user_id))
        # 自动更新会员等级
        update_user_level(conn, user_id, points)
        conn.commit()
        conn.close()
        flash('会员积分已更新', 'success')
        return redirect(url_for('admin_membership'))

# ── 辅助函数 ────────────────────────────────────────────────────
def add_user_points(user_id, points, type, description):
    """为用户添加积分"""
    conn = get_db()
    try:
        # 添加积分记录
        conn.execute('''
            INSERT INTO user_points (user_id, points, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, points, type, description))
        
        # 更新用户总积分
        current_points = conn.execute('SELECT points FROM users WHERE id=?', (user_id,)).fetchone()[0]
        new_points = current_points + points
        conn.execute('UPDATE users SET points=? WHERE id=?', (new_points, user_id))
        
        # 自动更新会员等级
        update_user_level(conn, user_id, new_points)
        
        conn.commit()
    finally:
        conn.close()

def update_user_level(conn, user_id, points):
    """根据积分更新用户等级"""
    # 获取当前积分对应的等级
    level = conn.execute('''
        SELECT id FROM membership_levels 
        WHERE min_points <= ? 
        AND (max_points IS NULL OR max_points >= ?) 
        ORDER BY min_points DESC 
        LIMIT 1
    ''', (points, points)).fetchone()
    
    if level:
        conn.execute('UPDATE users SET level_id=? WHERE id=?', (level[0], user_id))
