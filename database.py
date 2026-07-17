# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'gym.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 导入密码加密函数
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from auth import hash_password
    
    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        name TEXT,
        phone TEXT,
        avatar TEXT DEFAULT NULL,
        course_quota INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 课程表
    c.execute('''CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        duration INTEGER DEFAULT 60,  -- 课程时长（分钟）
        price REAL DEFAULT 200,
        category TEXT,  -- 课程类别
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 教练信息表
    c.execute('''CREATE TABLE IF NOT EXISTS coaches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        bio TEXT,
        specialty TEXT,
        experience INTEGER DEFAULT 0,
        rating REAL DEFAULT 5.0,
        rating_count INTEGER DEFAULT 0,
        price REAL DEFAULT 200,
        schedule TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # 教练-课程关联表
    c.execute('''CREATE TABLE IF NOT EXISTS coach_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coach_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        FOREIGN KEY (coach_id) REFERENCES coaches(id),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    )''')
    
    # 预约表
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        coach_id INTEGER NOT NULL,
        course_id INTEGER,  -- 关联课程
        date TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        note TEXT,
        rating INTEGER,
        review TEXT,
        review_tags TEXT,  -- 评价标签，如：专业、耐心、负责等
        review_images TEXT,  -- 评价图片，多个图片URL用逗号分隔
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (coach_id) REFERENCES coaches(id),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    )''')
    
    # 教练可预约时间段
    c.execute('''CREATE TABLE IF NOT EXISTS time_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coach_id INTEGER NOT NULL,
        weekday INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY (coach_id) REFERENCES coaches(id)
    )''')
    
    # API Token 表
    c.execute('''CREATE TABLE IF NOT EXISTS tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # 初始化管理员
    c.execute("INSERT OR IGNORE INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
              ('admin', hash_password('admin123'), 'admin', '系统管理员'))
    c.execute("INSERT OR IGNORE INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
              ('coach1', hash_password('coach123'), 'coach', '张教练'))
    c.execute("INSERT OR IGNORE INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
              ('coach2', hash_password('coach123'), 'coach', '李教练'))
    c.execute("INSERT OR IGNORE INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
              ('coach3', hash_password('coach123'), 'coach', '王教练'))
    c.execute("INSERT OR IGNORE INTO users (username, password, role, name) VALUES (?, ?, ?, ?)",
              ('user1', hash_password('user123'), 'user', '测试用户'))
    
    # 初始化课程
    courses = [
        ('力量训练', '专注于肌肉力量提升，适合想要增肌的学员', 60, 200, '增肌'),
        ('有氧运动', '提高心肺功能，适合减脂和增强耐力', 45, 150, '减脂'),
        ('瑜伽', '提高柔韧性和平衡能力，适合所有人群', 60, 250, '柔韧性'),
        ('普拉提', '核心训练，改善体态和身体控制力', 50, 220, '核心'),
        ('运动康复', '针对受伤或术后恢复的专业训练', 60, 300, '康复'),
        ('功能性训练', '提高日常生活和运动中的功能表现', 55, 230, '功能')
    ]
    for course in courses:
        c.execute("INSERT OR IGNORE INTO courses (name, description, duration, price, category) VALUES (?, ?, ?, ?, ?)", course)
    
    # 初始化教练信息
    c.execute("INSERT OR IGNORE INTO coaches (user_id, bio, specialty, experience, rating, price) VALUES (?, ?, ?, ?, ?, ?)",
              (2, '资深健身教练，擅长增肌减脂，拥有8年教学经验，国家二级运动员。', '增肌减脂|体态矫正|力量训练', 8, 4.8, 200))
    c.execute("INSERT OR IGNORE INTO coaches (user_id, bio, specialty, experience, rating, price) VALUES (?, ?, ?, ?, ?, ?)",
              (3, '前国家队体能教练，专注于运动康复和功能训练。', '运动康复|功能训练|拉伸放松', 10, 4.9, 300))
    c.execute("INSERT OR IGNORE INTO coaches (user_id, bio, specialty, experience, rating, price) VALUES (?, ?, ?, ?, ?, ?)",
              (4, '瑜伽导师，擅长普拉提和柔韧训练，帮助学员提升身体控制力。', '瑜伽|普拉提|柔韧训练', 6, 4.7, 250))
    
    # 初始化教练-课程关联
    # 张教练：力量训练、有氧运动
    c.execute("INSERT OR IGNORE INTO coach_courses (coach_id, course_id) VALUES (?, ?)", (1, 1))
    c.execute("INSERT OR IGNORE INTO coach_courses (coach_id, course_id) VALUES (?, ?)", (1, 2))
    # 李教练：运动康复、功能性训练
    c.execute("INSERT OR IGNORE INTO coach_courses (coach_id, course_id) VALUES (?, ?)", (2, 5))
    c.execute("INSERT OR IGNORE INTO coach_courses (coach_id, course_id) VALUES (?, ?)", (2, 6))
    # 王教练：瑜伽、普拉提
    c.execute("INSERT OR IGNORE INTO coach_courses (coach_id, course_id) VALUES (?, ?)", (3, 3))
    c.execute("INSERT OR IGNORE INTO coach_courses (coach_id, course_id) VALUES (?, ?)", (3, 4))
    

    
    # 初始化教练时间表（周一到周五）
    for coach_id in [1, 2, 3]:
        for weekday in range(1, 6):
            c.execute("INSERT OR IGNORE INTO time_slots (coach_id, weekday, start_time, end_time) VALUES (?, ?, ?, ?)",
                      (coach_id, weekday, '09:00', '12:00'))
            c.execute("INSERT OR IGNORE INTO time_slots (coach_id, weekday, start_time, end_time) VALUES (?, ?, ?, ?)",
                      (coach_id, weekday, '14:00', '18:00'))
            c.execute("INSERT OR IGNORE INTO time_slots (coach_id, weekday, start_time, end_time) VALUES (?, ?, ?, ?)",
                      (coach_id, weekday, '19:00', '21:00'))
    
    # 反馈表
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        subject TEXT NOT NULL,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    

    
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_PATH}")

if __name__ == '__main__':
    init_db()
