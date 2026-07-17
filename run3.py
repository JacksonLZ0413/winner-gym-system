#!/usr/bin/env python3
import paramiko, time, sys, os

HOST, PORT = '47.108.74.95', 22
USER, PASS = 'root', 'root123@'
PATH = '/var/www/winnerexe'

def cmd(ssh, c):
    s,i,o,e = ssh.exec_command(c)
    i.wait()
    return o.read().decode('utf-8', errors='ignore') or e.read().decode('utf-8', errors='ignore')

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    known_hosts = os.path.expanduser('~/.ssh/known_hosts')
    if os.path.exists(known_hosts):
        try:
            ssh.load_host_keys(known_hosts)
        except:
            pass
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15, allow_agent=False, look_for_keys=False)
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
