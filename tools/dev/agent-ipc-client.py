#!/usr/bin/env python3
import json
import socket
import sys

SOCK = "/run/ai-distro/agent.sock"

if len(sys.argv) < 2:
    print("usage: agent-ipc-client.py '<json>'")
    sys.exit(1)

payload = sys.argv[1]

try:
    req = json.loads(payload)
except json.JSONDecodeError as e:
    print(f"invalid json: {e}")
    sys.exit(2)

req_line = json.dumps(req) + "\n"

try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCK)
        s.sendall(req_line.encode("utf-8"))
        data = s.recv(4096)
        if data:
            sys.stdout.write(data.decode("utf-8"))
except FileNotFoundError:
    print(f"socket not found: {SOCK}")
    sys.exit(3)
except ConnectionRefusedError:
    print(f"connection refused: {SOCK}")
    sys.exit(4)
