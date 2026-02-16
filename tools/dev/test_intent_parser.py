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

def test_open_url():
    res = run("go to docs.openai.com")
    assert res["intent"] == "open_url"
    assert res["payload"] == "https://docs.openai.com"


def test_open_app():
    res = run("open firefox")
    assert res["intent"] == "open_app"
    assert res["payload"] == "firefox"


def test_remember():
    res = run("remember that my printer is in the office")
    assert res["intent"] == "remember"
    assert res["payload"] == "my printer is in the office"


def test_list_files():
    res = run("list files in /home/jmt3")
    assert res["intent"] == "list_files"
    assert res["payload"] == "/home/jmt3"

def test_plan_day_outfit():
    res = run("what should i wear today")
    assert res["intent"] == "plan_day_outfit"
    assert res["payload"] == "today"

def test_weather_get():
    res = run("weather tomorrow")
    assert res["intent"] == "weather_get"
    assert res["payload"] == "tomorrow"

def test_calendar_list_day():
    res = run("what is on my calendar today")
    assert res["intent"] == "calendar_list_day"
    assert res["payload"] == "today"

def test_email_summary():
    res = run("summarize my email")
    assert res["intent"] == "email_inbox_summary"
    assert res["payload"] == "in:inbox newer_than:2d"

def test_email_search():
    res = run("search my email for invoice")
    assert res["intent"] == "email_search"
    assert res["payload"] == "invoice"


if __name__ == "__main__":
    test_install_multiple()
    test_update()
    test_volume()
    test_open_url()
    test_open_app()
    test_remember()
    test_list_files()
    test_plan_day_outfit()
    test_weather_get()
    test_calendar_list_day()
    test_email_summary()
    test_email_search()
    print("ok")
