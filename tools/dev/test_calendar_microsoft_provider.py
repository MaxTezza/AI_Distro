#!/usr/bin/env python3
import datetime as dt
import importlib.util
from pathlib import Path


def load_module():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "tools" / "agent" / "calendar_microsoft_tool.py"
    spec = importlib.util.spec_from_file_location("calendar_microsoft_tool", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_list_day_formats_graph_items():
    mod = load_module()
    mod.resolve_day = lambda _: dt.date(2026, 2, 17)
    mod.graph_get = lambda token, url: {
        "value": [
            {
                "subject": "Team sync",
                "start": {"dateTime": "2026-02-17T09:00:00"},
            },
            {
                "subject": "Dentist",
                "start": {"dateTime": "2026-02-17T15:00:00"},
            },
        ]
    }
    out = mod.list_day("tok", "today")
    assert "Events for 2026-02-17" in out
    assert "Team sync" in out
    assert "Dentist" in out


def test_add_event_builds_graph_body():
    mod = load_module()
    mod.resolve_day = lambda _: dt.date(2026, 2, 17)
    seen = {}

    def fake_post(token, url, body):
        seen["token"] = token
        seen["url"] = url
        seen["body"] = body
        return {"subject": body.get("subject", "")}

    mod.graph_post = fake_post
    out = mod.add_event("tok", "today|3pm|Project review|business|false")
    assert out == "Added calendar event: Project review."
    assert seen["token"] == "tok"
    assert seen["url"] == "https://graph.microsoft.com/v1.0/me/events"
    assert seen["body"]["subject"] == "Project review"
    assert seen["body"]["start"]["dateTime"] == "2026-02-17T15:00:00"


def main():
    test_list_day_formats_graph_items()
    test_add_event_builds_graph_body()
    print("ok")


if __name__ == "__main__":
    main()
