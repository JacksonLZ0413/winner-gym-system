# 健身房私教预约系统 (GymCoach)

一个完整的健身房私教预约管理系统，支持用户、教练、管理员三种角色。

## 功能特性

### 用户端
- 用户注册/登录
- 浏览教练列表（头像、简介、擅长项目、评分）
- 查看教练可预约时间段
- 预约/取消课程
- 查看我的预约记录
- 对已完成课程评价打分

### 教练端
- 教练登录
- 设置可预约时间段（每周固定排班）
- 查看/确认/拒绝预约
- 查看学员评价

### 管理员端
- 管理教练账号
- 管理用户账号
- 查看预约统计数据

## 技术栈
- 后端：Flask (Python)
- 数据库：SQLite
- 前端：HTML + CSS + JavaScript

## 运行方式

```bash
# 安装依赖
pip install flask

# 启动服务
python app.py

# 访问 http://localhost:5000
```

## 默认账号

- 管理员：admin / admin123
- 教练：coach1 / coach123
- 用户：user1 / user123

## 项目结构

```
gym_coach/
├── app.py              # 主应用
├── database.py        # 数据库初始化
├── models.py          # 数据模型
├── static/
│   ├── css/
│   │   └── style.css   # 样式
│   └── js/
│       └── main.js     # 前端脚本
└── templates/
    ├── base.html       # 基础模板
    ├── index.html      # 首页
    ├── login.html      # 登录
    ├── register.html  # 注册
    ├── coaches.html    # 教练列表
    ├── coach.html      # 教练详情/预约
    ├── my_bookings.html # 我的预约
    ├── coach_dashboard.html # 教练后台
    └── admin.html      # 管理员后台
```
