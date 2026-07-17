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
    print("Winner Train - 安装依赖并启动")
    print("=" * 50)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=10)

    print("\n[1/4] 更新 requirements.txt...")
    with open(r'd:\winnerexe\requirements.txt', 'rb') as f:
        content = f.read()
    sftp = ssh.open_sftp()
    sftp.putfo(open(r'd:\winnerexe\requirements.txt', 'rb'), f'{REMOTE_PATH}/requirements.txt')
    sftp.close()
    print("  上传完成")

    print("\n[2/4] 安装 bcrypt 依赖...")
    status, output, error = run_command(ssh, "pip3 install bcrypt==4.0.1 -q 2>&1")
    if status == 0:
        print("  bcrypt 安装成功")
    else:
        print(f"  输出: {output[:200]}")

    print("\n[3/4] 停止旧进程...")
    run_command(ssh, "pkill -f 'python.*app.py' 2>/dev/null")
    run_command(ssh, "pkill -f 'flask' 2>/dev/null")

    print("\n[4/4] 启动应用...")
    run_command(ssh, f"cd {REMOTE_PATH} && nohup python3 app.py > /tmp/app.log 2>&1 &")

    import time
    time.sleep(3)

    print("\n[检查] 应用状态...")
    status, output, _ = run_command(ssh, "ps aux | grep -v grep | grep 'python.*app.py'")
    if output.strip():
        print("  应用正在运行!")
    else:
        print("  检查日志...")
        status, log, _ = run_command(ssh, "cat /tmp/app.log 2>/dev/null | tail -30")
        print(log if log else "无日志")

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
