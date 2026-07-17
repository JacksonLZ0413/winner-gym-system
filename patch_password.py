#!/usr/bin/env python3
"""补丁：添加管理员重置用户密码 + 修改自身密码功能"""

import os

APP_PATH = '/var/www/gym_coach/app.py'
TEMPLATE_DIR = '/var/www/gym_coach/templates'

# ── 要插入的新路由代码 ──
NEW_ROUTES = '''

# ═══════════════════════════════════════════════════════════════
# 新增功能：管理员重置用户密码
# ═══════════════════════════════════════════════════════════════
@app.route('/admin/users/reset_password', methods=['POST'])
def admin_reset_user_password():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    if not validate_csrf():
        flash('请求无效，请重试', 'error')
        return redirect(url_for('admin_users'))
    uid = request.form.get('user_id')
    new_pwd = request.form.get('new_password', '').strip()
    if not new_pwd or len(new_pwd) < 4:
        flash('密码长度至少4位', 'error')
        return redirect(url_for('admin_users'))
    hashed = hash_password(new_pwd)
    conn = get_db()
    conn.execute('UPDATE users SET password=? WHERE id=?', (hashed, uid))
    conn.commit()
    u = conn.execute('SELECT name FROM users WHERE id=?', (uid,)).fetchone()
    uname = u['name'] if u else uid
    conn.close()
    flash('已重置 %s 的密码' % uname, 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/change_password', methods=['GET', 'POST'])
def admin_change_password():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template('admin_change_password.html')
    if not validate_csrf():
        flash('请求无效，请重试', 'error')
        return redirect(url_for('admin_change_password'))
    old_pwd = request.form.get('old_password', '')
    new_pwd = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    if not old_pwd or not new_pwd or not confirm:
        flash('请填写所有字段', 'error')
        return redirect(url_for('admin_change_password'))
    if len(new_pwd) < 4:
        flash('新密码长度至少4位', 'error')
        return redirect(url_for('admin_change_password'))
    if new_pwd != confirm:
        flash('两次输入的新密码不一致', 'error')
        return redirect(url_for('admin_change_password'))
    conn = get_db()
    row = conn.execute('SELECT password FROM users WHERE id=?', (session['user_id'],)).fetchone()
    if not row or row['password'] != hash_password(old_pwd):
        conn.close()
        flash('原密码错误', 'error')
        return redirect(url_for('admin_change_password'))
    conn.execute('UPDATE users SET password=? WHERE id=?', (hash_password(new_pwd), session['user_id']))
    conn.commit()
    conn.close()
    flash('密码修改成功', 'success')
    return redirect(url_for('admin_change_password'))

'''

# ── 要插入的新 CSRF 字段（在 admin 用户列表模板中） ──
ADMIN_USERS_PATCH = '''<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'''

# ── 检查是否已有这些路由 ──
with open(APP_PATH, 'r') as f:
    content = f.read()

if 'admin_reset_user_password' in content:
    print('路由已存在，跳过 app.py 修改')
else:
    # 在 hash_password 函数之后找合适位置插入
    # 找到 "新增功能：教练课时统计" 那行，在前面插入
    marker = "# ═══════════════════════════════════════════════════════════════\n# 新增功能：教练课时统计"
    if marker in content:
        content = content.replace(marker, NEW_ROUTES.rstrip() + '\n\n' + marker)
    else:
        # 找最后一个 route 函数的末尾
        content = content.rstrip() + '\n' + NEW_ROUTES
    with open(APP_PATH, 'w') as f:
        f.write(content)
    print('app.py 已更新：添加密码管理路由')

# ── 创建修改密码模板 ──
tmpl_path = os.path.join(TEMPLATE_DIR, 'admin_change_password.html')
with open(tmpl_path, 'w') as f:
    f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>修改密码 - 管理后台</title>
<style>
body{font-family:-apple-system,sans-serif;background:#f5f5f5;margin:0}
.navbar{background:#1a1a2e;color:white;padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center}
.navbar a{color:white;text-decoration:none;margin-left:1.5rem}
.container{max-width:500px;margin:2rem auto;padding:0 1rem}
.card{background:white;border-radius:12px;padding:2rem;box-shadow:0 2px 8px rgba(0,0,0,0.08)}
h2{margin-top:0}
label{display:block;margin-bottom:0.3rem;font-weight:600;color:#333}
input[type="password"],input[type="text"]{width:100%;padding:0.7rem;border:1px solid #ddd;border-radius:8px;font-size:1rem;box-sizing:border-box;margin-bottom:1rem}
.btn{display:inline-block;padding:0.7rem 1.5rem;border:none;border-radius:8px;font-size:1rem;cursor:pointer;background:#667eea;color:white}
.btn:hover{background:#5a6fd6}
.btn-back{background:#eee;color:#333;text-decoration:none;margin-left:0.5rem}
.flash{padding:0.8rem 1rem;border-radius:8px;margin-bottom:1rem}
.flash-success{background:#d4edda;color:#155724}
.flash-error{background:#f8d7da;color:#721c24}
.form-group{margin-bottom:1rem}
</style>
</head>
<body>
<nav class="navbar">
    <span style="font-size:1.2rem;font-weight:bold">修改密码</span>
    <div><a href="/admin">返回后台</a></div>
</nav>
<div class="container">
    <div class="card">
        <h2>修改管理员密码</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, msg in messages %}
        <div class="flash flash-{{ category }}">{{ msg }}</div>
        {% endfor %}
        {% endwith %}
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <div class="form-group">
                <label>原密码</label>
                <input type="password" name="old_password" required>
            </div>
            <div class="form-group">
                <label>新密码（至少4位）</label>
                <input type="password" name="new_password" required>
            </div>
            <div class="form-group">
                <label>确认新密码</label>
                <input type="password" name="confirm_password" required>
            </div>
            <button type="submit" class="btn">修改密码</button>
        </form>
    </div>
</div>
</body>
</html>
''')
print('已创建 admin_change_password.html')

# ── 更新 admin_users.html，在每个用户行添加重置密码按钮 ──
admin_users_path = os.path.join(TEMPLATE_DIR, 'admin_users.html')
if os.path.exists(admin_users_path):
    with open(admin_users_path, 'r') as f:
        uc = f.read()
    if 'reset_password' not in uc:
        # 在 </tbody> 之前添加 reset 密码表单
        # 找到每行用户的删除按钮后面，添加重置密码
        old_end = '</tbody>'
        new_code = '''</tbody>
</table>
<h3 style="margin-top:2rem">重置用户密码</h3>
<form method="POST" action="/admin/users/reset_password">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:1rem">
        <select name="user_id" style="padding:0.5rem;border:1px solid #ddd;border-radius:6px;font-size:0.95rem">
            {% for u in users %}
            <option value="{{ u.id }}">{{ u.name }} ({{ u.username }})</option>
            {% endfor %}
        </select>
        <input type="text" name="new_password" placeholder="输入新密码（至少4位）" required style="padding:0.5rem;border:1px solid #ddd;border-radius:6px;width:200px">
        <button type="submit" style="padding:0.5rem 1rem;background:#e94560;color:white;border:none;border-radius:6px;cursor:pointer">重置密码</button>
    </div>
</form'''
        uc = uc.replace(old_end, new_code + '>')
        with open(admin_users_path, 'w') as f:
            f.write(uc)
        print('已更新 admin_users.html：添加重置密码功能')
    else:
        print('admin_users.html 已有重置密码功能，跳过')
else:
    print('警告：admin_users.html 不存在')

# ── 更新 admin.html，在菜单里添加修改密码入口 ──
admin_path = os.path.join(TEMPLATE_DIR, 'admin.html')
if os.path.exists(admin_path):
    with open(admin_path, 'r') as f:
        ac = f.read()
    if 'change_password' not in ac:
        # 在课程管理按钮后面添加
        ac = ac.replace(
            '<a href="/admin/users/courses" class="btn btn-primary">📚 课程管理</a>',
            '<a href="/admin/users/courses" class="btn btn-primary">📚 课程管理</a>\n        <a href="/admin/change_password" class="btn btn-secondary">🔑 修改密码</a>'
        )
        with open(admin_path, 'w') as f:
            f.write(ac)
        print('已更新 admin.html：添加修改密码菜单')
    else:
        print('admin.html 已有修改密码菜单，跳过')

print('\\n全部完成！请重启服务：')
print('pkill gunicorn && cd /var/www/gym_coach && gunicorn -w 2 -b 0.0.0.0:80 app:app --daemon')
