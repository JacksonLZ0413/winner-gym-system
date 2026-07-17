@echo off
chcp 65001 >nul
cd /d "C:\Users\Work&Study\.qclaw\workspace\gym_coach"

echo 正在初始化数据库...
"C:\Users\Work&Study\AppData\Local\Python\bin\python.exe" -c "from database import init_db; init_db()"

echo.
echo 正在启动服务器...
echo 访问地址: http://127.0.0.1:5000
echo.
"C:\Users\Work&Study\AppData\Local\Python\bin\python.exe" app.py

pause
