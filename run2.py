#!/usr/bin/env python3
import paramiko, time, sys

HOST, PORT = '47.108.74.95', 22
USER, PASS = 'root', 'root123@'
PATH = '/var/www/winnerexe'

def cmd(ssh, c):
    s,i,o,e = ssh.exec_command(c)
    i.wait()
    return o.read().decode() or e.read().decode()

try:
    ssh = paramiko.SSHClient()
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)
    print("1. 安装bcrypt...")
    print(cmd(ssh, "pip3 install bcrypt -q"))
    print("2. 停止旧进程...")
    cmd(ssh, "pkill -f app.py 2>/dev/null; true")
    time.sleep(1)
    print("3. 启动...")
    cmd(ssh, f"cd {PATH} && nohup python3 app.py > /tmp/a.log 2>&1 &")
    time.sleep(3)
    print("4. 检查...")
    r = cmd(ssh, "ps aux|grep app.py|grep -v grep")
    print(r or "无进程")
    l = cmd(ssh, "tail -15 /tmp/a.log")
    print(l or "无日志")
    ssh.close()
    print(f"\nOK - http://{HOST}:5001")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
