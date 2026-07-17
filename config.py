# -*- coding: utf-8 -*-

import os

# 配置信息
class Config:
    SECRET_KEY = 'gym_coach_secret_key_2024_fixed'
    DB_PATH = os.path.join(os.path.dirname(__file__), 'gym.db')
    PERMANENT_SESSION_LIFETIME = 7  # 7天
    
    # 登录限流配置
    RATE_LIMIT_MAX_ATTEMPTS = 5
    RATE_LIMIT_WINDOW = 300  # 5分钟
    
    # JWT配置
    JWT_SECRET_KEY = 'jwt_secret_key_for_miniprogram_2024'
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7  # 7天
