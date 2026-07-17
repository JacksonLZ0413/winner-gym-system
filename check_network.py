import paramiko
HOST, PORT = '47.108.74.95', 22
USER, PASS = 'root', 'root123@'

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)

    print("1. 检查端口监听...")
    stdin, stdout, stderr = ssh.exec_command("netstat -tlnp | grep 5001")
    stdin.close()
    print(stdout.read().decode())

    print("\n2. 检查防火墙...")
    stdin, stdout, stderr = ssh.exec_command("ufw status 2>/dev/null || firewall-cmd --list-all 2>/dev/null || iptables -L 2>/dev/null | head -20")
    stdin.close()
    print(stdout.read().decode())

    print("\n3. 检查进程...")
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep app.py")
    stdin.close()
    print(stdout.read().decode())

    ssh.close()
except Exception as e:
    print(f"Error: {e}")
