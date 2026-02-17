#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

from provider_config import load_providers


def main():
    if len(sys.argv) < 2:
        print("usage: calendar_router.py add|list [payload]")
        return 2
    cmd = sys.argv[1].strip().lower()
    payload = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    providers = load_providers()
    provider = providers.get("calendar", "local")

    here = Path(__file__).resolve().parent
    local_tool = str(here / "calendar_tool.py")
    google_tool = str(here / "calendar_google_tool.py")
    microsoft_tool = str(here / "calendar_microsoft_tool.py")
    tool = local_tool
    if provider == "google":
        tool = google_tool
    elif provider == "microsoft":
        tool = microsoft_tool

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


if __name__ == "__main__":
    raise SystemExit(main())
