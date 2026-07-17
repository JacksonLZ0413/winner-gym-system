import paramiko
HOST, PORT = '47.108.74.95', 22
USER, PASS = 'root', 'root123@'
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)
    print("connected")
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
