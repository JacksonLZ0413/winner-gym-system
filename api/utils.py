# -*- coding: utf-8 -*-
import sqlite3
import os
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)

def rows_to_list(rows):
    return [row_to_dict(row) for row in rows]

def success_response(data=None, message='success'):
    return {
        'code': 0,
        'message': message,
        'data': data
    }

def error_response(message='error', code=-1):
    return {
        'code': code,
        'message': message,
        'data': None
    }