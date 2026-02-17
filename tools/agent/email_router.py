#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

from provider_config import load_providers


def main():
    if len(sys.argv) < 2:
        print("usage: email_router.py summary|search|draft [payload]")
        return 2
    cmd = sys.argv[1].strip().lower()
    payload = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    providers = load_providers()
    provider = providers.get("email", "gmail")
    here = Path(__file__).resolve().parent

    if provider == "gmail":
        tool = str(here / "gmail_tool.py")
        proc = subprocess.run(
            [sys.executable, tool, cmd, payload],
            text=True,
            capture_output=True,
        )
        if proc.stdout:
            print(proc.stdout.strip())
        if proc.returncode != 0 and proc.stderr:
            print(proc.stderr.strip(), file=sys.stderr)
        return proc.returncode

    print(f"Email provider '{provider}' is not configured yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

