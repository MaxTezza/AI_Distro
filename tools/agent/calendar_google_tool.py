#!/usr/bin/env python3
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request


def oauth_cfg():
    path = os.environ.get(
        "AI_DISTRO_GOOGLE_CALENDAR_OAUTH_FILE",
        os.path.expanduser("~/.config/ai-distro/google-calendar-oauth.json"),
    )
    cfg = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            cfg.update(raw)
    except Exception:
        pass
    for env_key, dst in (
        ("AI_DISTRO_GOOGLE_CLIENT_ID", "client_id"),
        ("AI_DISTRO_GOOGLE_CLIENT_SECRET", "client_secret"),
        ("AI_DISTRO_GOOGLE_REFRESH_TOKEN", "refresh_token"),
        ("AI_DISTRO_GOOGLE_CALENDAR_ID", "calendar_id"),
    ):
        val = os.environ.get(env_key, "").strip()
        if val:
            cfg[dst] = val
    if not str(cfg.get("calendar_id", "")).strip():
        cfg["calendar_id"] = "primary"
    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not str(cfg.get(k, "")).strip()]
    return None if missing else cfg


def access_token(cfg):
    body = urllib.parse.urlencode(
        {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "refresh_token": cfg["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    tok = str(payload.get("access_token", "")).strip()
    return tok or None


def resolve_day(day_text):
    today = dt.date.today()
    if (day_text or "").strip().lower() == "tomorrow":
        return today + dt.timedelta(days=1)
    return today


def normalize_time(raw):
    s = (raw or "").strip().lower()
    if not s:
        return "09:00"
    # 3pm / 3:30pm / 14:30
    import re
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", s)
    if not m:
        return "09:00"
    h = int(m.group(1))
    mm = int(m.group(2) or "0")
    ap = m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    h = max(0, min(h, 23))
    mm = max(0, min(mm, 59))
    return f"{h:02d}:{mm:02d}"


def list_day(token, cfg, day_text):
    day = resolve_day(day_text)
    start = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    params = urllib.parse.urlencode(
        {
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeMin": start.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "timeMax": end.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "maxResults": "20",
        }
    )
    cal_id = urllib.parse.quote(str(cfg.get("calendar_id", "primary")), safe="")
    url = f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    items = payload.get("items", [])
    if not isinstance(items, list) or not items:
        return f"No events found for {day.isoformat()}."
    lines = [f"Events for {day.isoformat()}:"]
    for it in items[:12]:
        if not isinstance(it, dict):
            continue
        summary = str(it.get("summary", "event")).strip() or "event"
        start_obj = it.get("start", {})
        when = ""
        if isinstance(start_obj, dict):
            when = str(start_obj.get("dateTime") or start_obj.get("date") or "").strip()
        lines.append(f"- {when} {summary}".strip())
    return "\n".join(lines)


def add_event(token, cfg, payload):
    parts = [p.strip() for p in (payload or "").split("|")]
    if len(parts) < 3:
        return "invalid event payload"
    day = resolve_day(parts[0] or "today")
    hhmm = normalize_time(parts[1] or "09:00")
    title = parts[2] or "New event"
    start_dt = f"{day.isoformat()}T{hhmm}:00"
    end_h = min(int(hhmm.split(":")[0]) + 1, 23)
    end_dt = f"{day.isoformat()}T{end_h:02d}:{hhmm.split(':')[1]}:00"
    tz = os.environ.get("AI_DISTRO_TIMEZONE", "UTC")
    body = {
        "summary": title,
        "start": {"dateTime": start_dt, "timeZone": tz},
        "end": {"dateTime": end_dt, "timeZone": tz},
    }
    cal_id = urllib.parse.quote(str(cfg.get("calendar_id", "primary")), safe="")
    url = f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        out = json.loads(resp.read().decode("utf-8", errors="ignore"))
    summary = str(out.get("summary", title)).strip() or title
    return f"Added calendar event: {summary}."


def main():
    if len(sys.argv) < 2:
        print("usage: calendar_google_tool.py add|list [payload]")
        return 2
    cfg = oauth_cfg()
    if not cfg:
        print("Google Calendar OAuth not configured.")
        return 0
    try:
        token = access_token(cfg)
        if not token:
            print("Unable to acquire Google Calendar access token.")
            return 0
    except Exception:
        print("Unable to acquire Google Calendar access token.")
        return 0

    cmd = sys.argv[1].strip().lower()
    payload = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    try:
        if cmd == "list":
            print(list_day(token, cfg, payload or "today"))
            return 0
        if cmd == "add":
            print(add_event(token, cfg, payload))
            return 0
    except Exception:
        print("Google Calendar request failed.")
        return 0
    print("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

