# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../gym.db')

def migrate_for_miniprogram():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'openid' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN openid TEXT")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_openid ON users(openid)")
        print("Added openid column and index")
    
    if 'unionid' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN unionid TEXT")
        print("Added unionid column")
    
    conn.commit()
    conn.close()
    print("数据库迁移完成")

if __name__ == '__main__':
    migrate_for_miniprogram()