@echo off
chcp 65001 >nul
cd /d "D:\winnerexe"
echo ================================
echo  健身房预约系统 - 服务启动
echo ================================
echo.
echo 服务器地址: http://localhost:5001
echo API地址:    http://localhost:5001/api
echo.
echo 请先在微信开发者工具中打开 miniprogram 目录
echo 确保已勾选 "不校验合法域名"
echo.
echo 正在启动服务器...
echo.
python app.py
pause
