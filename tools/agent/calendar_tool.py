#!/usr/bin/env python3
import datetime as dt
import json
import os
import re
import sys
from typing import Dict, List, Optional


def events_path() -> str:
    return os.environ.get(
        "AI_DISTRO_CALENDAR_EVENTS_FILE",
        os.path.expanduser("~/.config/ai-distro/calendar-events.json"),
    )


def _ensure_parent(path: str):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_events() -> List[Dict]:
    path = events_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
    except Exception:
        pass
    return []


def save_events(events: List[Dict]):
    path = events_path()
    _ensure_parent(path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(events, fh, indent=2)
        fh.write("\n")


def resolve_day(day_text: str) -> dt.date:
    today = dt.date.today()
    t = (day_text or "today").strip().lower()
    if t == "tomorrow":
        return today + dt.timedelta(days=1)
    return today


def normalize_time(raw: str) -> str:
    s = raw.strip().lower()
    # 3pm / 3:30pm / 03:30
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", s)
    if not m:
        return "09:00"
    hour = int(m.group(1))
    minute = int(m.group(2) or "0")
    ap = m.group(3)
    if ap == "pm" and hour < 12:
        hour += 12
    if ap == "am" and hour == 12:
        hour = 0
    hour = max(0, min(hour, 23))
    minute = max(0, min(minute, 59))
    return f"{hour:02d}:{minute:02d}"


def add_event(payload: str) -> str:
    # payload format: <day>|<time>|<title>|<dress_code>|<outdoor>
    parts = [p.strip() for p in (payload or "").split("|")]
    if len(parts) < 3:
        return "invalid event payload"
    day = resolve_day(parts[0] or "today")
    start = normalize_time(parts[1] or "09:00")
    title = parts[2] or "New event"
    dress = (parts[3] if len(parts) > 3 and parts[3] else "casual").lower()
    if dress not in ("casual", "business", "formal"):
        dress = "casual"
    outdoor = False
    if len(parts) > 4:
        outdoor = parts[4].lower() in ("1", "true", "yes", "outdoor")
    events = load_events()
    events.append(
        {
            "date": day.isoformat(),
            "start": start,
            "title": title,
            "dress_code": dress,
            "outdoor": outdoor,
        }
    )
    save_events(events)
    return f"Added calendar event for {day.isoformat()} at {start}: {title}."


def list_day(day_text: str) -> str:
    day = resolve_day(day_text)
    date_s = day.isoformat()
    events = [e for e in load_events() if str(e.get("date", "")).strip() == date_s]
    if not events:
        return f"No events found for {date_s}."
    events.sort(key=lambda e: str(e.get("start", "")))
    lines = [f"Events for {date_s}:"]
    for e in events[:12]:
        lines.append(f"- {e.get('start', '??:??')} {e.get('title', 'event')}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("usage: calendar_tool.py add|list [payload]")
        return
    cmd = sys.argv[1].strip().lower()
    payload = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    if cmd == "add":
        print(add_event(payload))
        return
    if cmd == "list":
        print(list_day(payload or "today"))
        return
    print("unknown command")


if __name__ == "__main__":
    main()

