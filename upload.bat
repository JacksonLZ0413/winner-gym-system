@echo off
echo ========================================
echo Winner Train 上传脚本
echo ========================================
echo.

set SERVER=root@47.108.74.95
set PASSWORD=root123@
set REMOTE_PATH=/var/www/winnerexe

echo [1/4] 创建远程目录...
echo %PASSWORD% | plink -batch %SERVER% "mkdir -p %REMOTE_PATH%"
if errorlevel 1 goto :error

echo [2/4] 上传文件...
echo y | pscp -r -pw %PASSWORD% templates %SERVER%:%REMOTE_PATH%
echo y | pscp -r -pw %PASSWORD% static %SERVER%:%REMOTE_PATH%
echo y | pscp -r -pw %PASSWORD% *.py %SERVER%:%REMOTE_PATH%
echo y | pscp -r -pw %PASSWORD% *.txt %SERVER%:%REMOTE_PATH%
echo y | pscp -r -pw %PASSWORD% *.bat %SERVER%:%REMOTE_PATH%

echo [3/4] 安装依赖...
echo %PASSWORD% | plink -batch %SERVER% "cd %REMOTE_PATH% && pip install -r requirements.txt"

echo [4/4] 重启服务...
echo %PASSWORD% | plink -batch %SERVER% "systemctl restart gunicorn || supervisorctl restart all || echo 'Please restart service manually'"

echo.
echo ========================================
echo 上传完成！
echo ========================================
goto :end

:error
echo.
echo [错误] 上传失败，请检查网络连接和密码
pause

:end
pause
