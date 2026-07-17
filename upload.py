#!/usr/bin/env python3
import os
import sys
import paramiko
from pathlib import Path

HOST = '47.108.74.95'
PORT = 22
USERNAME = 'root'
PASSWORD = 'root123@'
REMOTE_PATH = '/var/www/winnerexe'

LOCAL_PATH = Path(__file__).parent

def upload_directory(sftp, local_dir, remote_dir):
    """递归上传目录"""
    for item in local_dir.iterdir():
        if item.name in ['__pycache__', '.git', '.pyc', 'node_modules', '*.pyc']:
            continue
        remote_path = f"{remote_dir}/{item.name}"
        if item.is_dir():
            try:
                sftp.stat(remote_path)
            except:
                sftp.mkdir(remote_path)
            upload_directory(sftp, item, remote_path)
        else:
            print(f"  上传: {item.name}")
            sftp.put(str(item), remote_path)

def main():
    print("=" * 50)
    print("Winner Train - 上传到阿里云ECS")
    print("=" * 50)

    print(f"\n[1/5] 连接到服务器 {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=10)

    print("[2/5] 创建远程目录...")
    stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {REMOTE_PATH}")
    stdout.channel.recv_exit_status()

    sftp = ssh.open_sftp()

    print("[3/5] 上传文件...")
    upload_directory(sftp, LOCAL_PATH, REMOTE_PATH)

    sftp.close()

    print("[4/5] 安装依赖...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_PATH} && pip install -r requirements.txt -q")
    stdout.channel.recv_exit_status()
    if stderr.read():
        print("  警告: 部分依赖安装可能有警告")

    print("[5/5] 重启服务...")
    commands = [
        "systemctl restart gunicorn 2>/dev/null",
        "supervisorctl restart all 2>/dev/null",
        "systemctl restart nginx 2>/dev/null",
        "pkill -f 'python.*app.py' ; cd /var/www/winnerexe && nohup python app.py &"
    ]
    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status == 0:
            break

    ssh.close()

    print("\n" + "=" * 50)
    print("✓ 上传完成！")
    print(f"  访问地址: http://{HOST}:5001")
    print("=" * 50)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[错误] {e}")
        sys.exit(1)
