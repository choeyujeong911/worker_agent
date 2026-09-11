import socket, struct, subprocess, tempfile
from pathlib import Path

HOST, PORT = "0.0.0.0", 5000
CENTRAL = "203.250.35.180"

def recv_n(s, n):
    b = b""
    while len(b) < n:
        x = s.recv(n - len(b))
        if not x:
            raise ConnectionError
        b += x
    return b

with socket.socket() as server:
    server.bind((HOST, PORT))
    server.listen()
    print(f"[READY] Worker Agent listening on {PORT}")
    print("[INFO] Press Ctrl+C to stop")

    try:
        while True:
            s, addr = server.accept()

            with s:
                print(f"[CONNECTED] {addr[0]}:{addr[1]}")

                if addr[0] != CENTRAL:
                    print("[DENIED]")
                    continue

                name = recv_n(s, struct.unpack("!I", recv_n(s, 4))[0]).decode()
                data = recv_n(s, struct.unpack("!Q", recv_n(s, 8))[0])

                print(f"[RECEIVED] {name} ({len(data)} bytes)")

                with tempfile.TemporaryDirectory() as d:
                    f = Path(d) / Path(name).name
                    f.write_bytes(data)

                    try:
                        if f.suffix == ".py":
                            cmd = ["python", str(f)]

                        elif f.suffix == ".java":
                            c = subprocess.run(["javac", str(f)], capture_output=True)
                            if c.returncode:
                                s.sendall(c.stderr)
                                continue
                            cmd = ["java", "-cp", d, f.stem]

                        elif f.suffix == ".c":
                            exe = Path(d) / "workload.exe"
                            c = subprocess.run(
                                ["gcc", "-O2", str(f), "-o", str(exe)],
                                capture_output=True
                            )
                            if c.returncode:
                                s.sendall(c.stderr)
                                continue
                            cmd = [str(exe)]

                        else:
                            s.sendall(b"Unsupported file type")
                            continue

                        print(f"[RUNNING] {name}")
                        r = subprocess.run(cmd, capture_output=True)
                        s.sendall(r.stdout + r.stderr)
                        print(f"[DONE] {name}")

                    except Exception as e:
                        s.sendall(str(e).encode())
                        print(f"[ERROR] {e}")

    except KeyboardInterrupt:
        print("\n[STOPPED] Worker Agent")