#!/usr/bin/env python3
import paramiko
import sys

HOST = '47.108.74.95'
PORT = 22
USERNAME = 'root'
PASSWORD = 'root123@'
REMOTE_PATH = '/var/www/winnerexe'

def run_command(ssh, cmd):
    """执行远程命令"""
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    return exit_status, output, error

def main():
    print("=" * 50)
    print("Winner Train - 服务器配置")
    print("=" * 50)

    print(f"\n[1/4] 连接到服务器 {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=10)

    print("[2/4] 检查项目文件...")
    status, output, _ = run_command(ssh, f"ls -la {REMOTE_PATH}")
    print(output)

    print("[3/4] 安装依赖...")
    status, output, error = run_command(ssh, f"cd {REMOTE_PATH} && pip install -r requirements.txt -q 2>&1")
    if status == 0:
        print("  依赖安装成功")
    else:
        print(f"  警告: {error[:200]}")

    print("[4/4] 重启服务...")
    commands = [
        ("systemctl daemon-reload", False),
        ("systemctl restart gunicorn 2>/dev/null || echo 'gunicorn not found'", True),
        ("systemctl restart nginx 2>/dev/null || echo 'nginx not found'", True),
        ("supervisorctl restart all 2>/dev/null || echo 'supervisor not found'", True),
        ("pkill -f 'python.*app.py' 2>/dev/null || echo 'no python process'", True),
    ]

    for cmd, critical in commands:
        status, output, error = run_command(ssh, cmd)
        if status == 0:
            print(f"  OK: {cmd[:50]}")
        else:
            print(f"  Skip: {cmd[:50]}")

    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && nohup python app.py > /tmp/app.log 2>&1 &")
    stdout.channel.recv_exit_status()

    print("\n[检查] 应用状态...")
    status, output, _ = run_command(ssh, "ps aux | grep -v grep | grep 'python.*app.py'")
    if output.strip():
        print("  应用正在运行!")
        print(f"  PID: {output.strip()}")
    else:
        print("  应用可能未运行，检查日志: /tmp/app.log")

    status, output, _ = run_command(ssh, "cat /tmp/app.log 2>/dev/null | tail -20")
    if output.strip():
        print("\n  最近日志:")
        print(output)

    ssh.close()

    print("\n" + "=" * 50)
    print("部署完成!")
    print(f"  请访问: http://{HOST}:5001")
    print("=" * 50)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
