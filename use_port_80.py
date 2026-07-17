import paramiko, time
HOST, PORT = '47.108.74.95', 22
USER, PASS = 'root', 'root123@'
PATH = '/var/www/winnerexe'

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)

    print("1. 停止旧进程...")
    stdin, stdout, stderr = ssh.exec_command("pkill -f app.py")
    stdin.close()
    time.sleep(2)

    print("\n2. 修改app.py使用80端口...")
    stdin, stdout, stderr = ssh.exec_command(f"sed -i 's/port=5001/port=80/g' {PATH}/app.py")
    stdin.close()
    print("配置已更新")

    print("\n3. 启动应用...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {PATH} && nohup python3 app.py > /tmp/app.log 2>&1 &")
    stdin.close()
    time.sleep(3)

    print("\n4. 检查端口...")
    stdin, stdout, stderr = ssh.exec_command("netstat -tlnp | grep 80")
    stdin.close()
    print(stdout.read().decode())

    ssh.close()
    print(f"\nDone! 请访问: http://{HOST}")
except Exception as e:
    print(f"Error: {e}")
