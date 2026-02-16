#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARSER = ROOT / "tools" / "dev" / "intent_parser.py"


def run(text: str):
    out = subprocess.check_output([sys.executable, str(PARSER), text], text=True)
    return json.loads(out)


def test_install_multiple():
    res = run("install vim and curl")
    assert res["intent"] == "package_install"
    assert res["payload"] == "vim,curl"


def test_update():
    res = run("update the system")
    assert res["intent"] == "system_update"
    assert res["payload"] == "stable"


def test_volume():
    res = run("set volume to 40%")
    assert res["intent"] == "set_volume"
    assert res["payload"] == "40"


if __name__ == "__main__":
    test_install_multiple()
    test_update()
    test_volume()
    print("ok")
