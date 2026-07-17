import paramiko, time
HOST, PORT = '47.108.74.95', 22
USER, PASS = 'root', 'root123@'
PATH = '/var/www/winnerexe'

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)

    # 1. Check bcrypt
    print("1. Check bcrypt...")
    stdin, stdout, stderr = ssh.exec_command("pip3 list | grep bcrypt")
    print(stdout.read().decode() or stderr.read().decode())

    # 2. Install bcrypt
    print("2. Install bcrypt...")
    stdin, stdout, stderr = ssh.exec_command("pip3 install bcrypt")
    stdin.close()
    print(stdout.read().decode()[:200])
    print(stderr.read().decode()[:200])

    # 3. Kill old process
    print("3. Kill old process...")
    stdin, stdout, stderr = ssh.exec_command("pkill -f app.py; true")
    stdin.close()
    time.sleep(1)

    # 4. Start app
    print("4. Start app...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {PATH} && nohup python3 app.py > /tmp/app.log 2>&1 &")
    stdin.close()
    time.sleep(3)

    # 5. Check process
    print("5. Check process...")
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep app.py | grep -v grep")
    stdin.close()
    r = stdout.read().decode()
    print(r[:300] if r else "No process")

    # 6. Check log
    print("6. Check log...")
    stdin, stdout, stderr = ssh.exec_command("tail -20 /tmp/app.log")
    stdin.close()
    l = stdout.read().decode()
    print(l[:500] if l else "No log")

    ssh.close()
    print(f"\nDone! http://{HOST}:5001")
except Exception as e:
    print(f"Error: {e}")
