#!/usr/bin/env python3
import paramiko
import sys

HOST = '47.108.74.95'
PORT = 22
USERNAME = 'root'
PASSWORD = 'root123@'
REMOTE_PATH = '/var/www/winnerexe'

def run_command(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    return exit_status, output

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=15)

    print("安装 bcrypt...")
    status, out = run_command(ssh, "pip3 install bcrypt==4.0.1 -q")
    print(f"pip结果: {status}")

    print("停止旧进程...")
    run_command(ssh, "pkill -f 'python.*app.py' 2>/dev/null")

    print("启动应用...")
    run_command(ssh, f"cd {REMOTE_PATH} && python3 app.py > /tmp/app.log 2>&1 &")

    import time
    time.sleep(3)

    status, out = run_command(ssh, "ps aux | grep -v grep | grep 'python.*app.py'")
    print(f"进程: {out}")

    status, log = run_command(ssh, "cat /tmp/app.log 2>/dev/null | tail -20")
    print(f"日志: {log}")

    ssh.close()
    print(f"访问: http://{HOST}:5001")

if __name__ == '__main__':
    main()
