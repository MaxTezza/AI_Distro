#!/usr/bin/env python3
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request


def oauth_config():
    path = os.environ.get(
        "AI_DISTRO_MICROSOFT_OUTLOOK_OAUTH_FILE",
        os.path.expanduser("~/.config/ai-distro/microsoft-outlook-oauth.json"),
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
        ("AI_DISTRO_MICROSOFT_CLIENT_ID", "client_id"),
        ("AI_DISTRO_MICROSOFT_CLIENT_SECRET", "client_secret"),
        ("AI_DISTRO_MICROSOFT_REFRESH_TOKEN", "refresh_token"),
        ("AI_DISTRO_MICROSOFT_TENANT_ID", "tenant_id"),
    ):
        val = os.environ.get(env_key, "").strip()
        if val:
            cfg[dst] = val

    if not str(cfg.get("tenant_id", "")).strip():
        cfg["tenant_id"] = "common"
    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not str(cfg.get(k, "")).strip()]
    return None if missing else cfg


def resolve_day(day_text):
    today = dt.date.today()
    if (day_text or "").strip().lower() == "tomorrow":
        return today + dt.timedelta(days=1)
    return today


def normalize_time(raw):
    s = (raw or "").strip().lower()
    if not s:
        return "09:00"
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


def access_token(cfg, scope):
    token_url = f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token"
    body = urllib.parse.urlencode(
        {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "refresh_token": cfg["refresh_token"],
            "grant_type": "refresh_token",
            "scope": scope,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    token = str(payload.get("access_token", "")).strip()
    return token or None


def graph_get(token, url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def graph_post(token, url, body):
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
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def list_day(token, day_text):
    day = resolve_day(day_text)
    tz = os.environ.get("AI_DISTRO_TIMEZONE", "UTC")
    start = dt.datetime.combine(day, dt.time.min)
    end = start + dt.timedelta(days=1)
    params = urllib.parse.urlencode(
        {
            "startDateTime": start.isoformat(),
            "endDateTime": end.isoformat(),
            "$orderby": "start/dateTime",
            "$top": "20",
        }
    )
    url = f"https://graph.microsoft.com/v1.0/me/calendarView?{params}"
    payload = graph_get(token, url)
    items = payload.get("value", [])
    if not isinstance(items, list) or not items:
        return f"No events found for {day.isoformat()}."

    lines = [f"Events for {day.isoformat()} ({tz}):"]
    for it in items[:12]:
        if not isinstance(it, dict):
            continue
        summary = str(it.get("subject", "event")).strip() or "event"
        start_obj = it.get("start", {})
        when = ""
        if isinstance(start_obj, dict):
            when = str(start_obj.get("dateTime") or "").strip()
        lines.append(f"- {when} {summary}".strip())
    return "\n".join(lines)


def add_event(token, payload):
    parts = [p.strip() for p in (payload or "").split("|")]
    if len(parts) < 3:
        return "invalid event payload"
    day = resolve_day(parts[0] or "today")
    hhmm = normalize_time(parts[1] or "09:00")
    title = parts[2] or "New event"
    tz = os.environ.get("AI_DISTRO_TIMEZONE", "UTC")
    start_dt = f"{day.isoformat()}T{hhmm}:00"
    end_h = min(int(hhmm.split(":")[0]) + 1, 23)
    end_dt = f"{day.isoformat()}T{end_h:02d}:{hhmm.split(':')[1]}:00"
    body = {
        "subject": title,
        "start": {"dateTime": start_dt, "timeZone": tz},
        "end": {"dateTime": end_dt, "timeZone": tz},
    }
    out = graph_post(token, "https://graph.microsoft.com/v1.0/me/events", body)
    summary = str(out.get("subject", title)).strip() or title
    return f"Added calendar event: {summary}."


def main():
    if len(sys.argv) < 2:
        print("usage: calendar_microsoft_tool.py add|list [payload]")
        return 2
    cmd = sys.argv[1].strip().lower()
    payload = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    if cmd not in ("add", "list"):
        print("unknown command")
        return 2

    cfg = oauth_config()
    if not cfg:
        print("Microsoft Calendar OAuth not configured.")
        return 0

    default_scope = (
        "offline_access https://graph.microsoft.com/Calendars.ReadWrite"
        if cmd == "add"
        else "offline_access https://graph.microsoft.com/Calendars.Read"
    )
    scope = os.environ.get("AI_DISTRO_MICROSOFT_CALENDAR_SCOPE", default_scope).strip() or default_scope
    try:
        token = access_token(cfg, scope)
        if not token:
            print("Unable to acquire Microsoft Calendar access token.")
            return 0
    except Exception:
        print("Unable to acquire Microsoft Calendar access token.")
        return 0

    try:
        if cmd == "list":
            print(list_day(token, payload or "today"))
            return 0
        print(add_event(token, payload))
        return 0
    except Exception:
        print("Microsoft Calendar request failed.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
