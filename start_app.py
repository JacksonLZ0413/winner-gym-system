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
    error = stderr.read().decode('utf-8', errors='ignore')
    return exit_status, output, error

def main():
    print("=" * 50)
    print("Winner Train - 修复并启动应用")
    print("=" * 50)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=10)

    print("\n[1/3] 检查 Python 版本...")
    status, output, _ = run_command(ssh, "which python3 || which python")
    print(f"  Python 路径: {output.strip()}")

    status, output, _ = run_command(ssh, "python3 --version 2>/dev/null || python --version")
    print(f"  版本: {output.strip()}")

    print("\n[2/3] 停止旧进程...")
    run_command(ssh, "pkill -f 'python.*app.py' 2>/dev/null")
    run_command(ssh, "pkill -f 'flask' 2>/dev/null")

    print("\n[3/3] 启动应用 (使用 python3)...")
    run_command(ssh, f"cd {REMOTE_PATH} && nohup python3 app.py > /tmp/app.log 2>&1 &")

    import time
    time.sleep(2)

    print("\n[检查] 应用状态...")
    status, output, _ = run_command(ssh, "ps aux | grep -v grep | grep 'python.*app.py'")
    if output.strip():
        print("  应用正在运行!")
        print(f"  {output.strip()}")
    else:
        print("  检查日志...")
        status, log, _ = run_command(ssh, "cat /tmp/app.log")
        print(log[-500:] if log else "无日志")

    ssh.close()
    print("\n" + "=" * 50)
    print(f"请访问: http://{HOST}:5001")
    print("=" * 50)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[错误] {e}")
        sys.exit(1)
