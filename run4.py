#!/usr/bin/env python3
import paramiko, time, sys

HOST, PORT = '47.108.74.95', 22
USER, PASS = 'root', 'root123@'
PATH = '/var/www/winnerexe'

def cmd(ssh, c):
    s = ssh.exec_command(c)
    i = s[1]
    o = s[2]
    e = s[3] if len(s) > 3 else s[2]
    i.wait()
    return (o.read() or b'').decode('utf-8', errors='ignore')

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    print("1. 连接成功")

    print("2. 安装bcrypt...")
    r = cmd(ssh, "pip3 install bcrypt -q 2>&1")
    print(r[:100] if r else "OK")

    print("3. 停止旧进程...")
    cmd(ssh, "pkill -f app.py 2>/dev/null; true")
    time.sleep(1)

    print("4. 启动...")
    cmd(ssh, f"cd {PATH} && nohup python3 app.py > /tmp/a.log 2>&1 &")
    time.sleep(3)

    print("5. 检查...")
    r = cmd(ssh, "ps aux|grep app.py|grep -v grep")
    print(r[:200] if r else "无进程")
    l = cmd(ssh, "tail -20 /tmp/a.log")
    print(l[:300] if l else "无日志")

    ssh.close()
    print(f"\n[OK] http://{HOST}:5001")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
