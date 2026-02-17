#!/usr/bin/env python3
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from provider_config import load_providers


def target_date(payload: str) -> dt.date:
    today = dt.date.today()
    p = (payload or "today").strip().lower()
    if p == "tomorrow":
        return today + dt.timedelta(days=1)
    return today


def load_calendar_events(day: dt.date):
    path = os.environ.get(
        "AI_DISTRO_CALENDAR_EVENTS_FILE",
        os.path.expanduser("~/.config/ai-distro/calendar-events.json"),
    )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:
        return []

    if not isinstance(raw, list):
        return []

    out = []
    date_s = day.isoformat()
    for item in raw:
        if not isinstance(item, dict):
            continue
        if str(item.get("date", "")).strip() != date_s:
            continue
        out.append(
            {
                "title": str(item.get("title", "event")).strip() or "event",
                "start": str(item.get("start", "")).strip(),
                "outdoor": bool(item.get("outdoor", False)),
                "dress_code": str(item.get("dress_code", "casual")).strip().lower(),
            }
        )
    return out


def _iso_utc(ts: dt.datetime) -> str:
    return ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_google_oauth():
    cfg_path = os.environ.get(
        "AI_DISTRO_GOOGLE_CALENDAR_OAUTH_FILE",
        os.path.expanduser("~/.config/ai-distro/google-calendar-oauth.json"),
    )
    cfg = {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            cfg.update(raw)
    except Exception:
        pass

    # Env vars override file values.
    for env_key, dst in (
        ("AI_DISTRO_GOOGLE_CLIENT_ID", "client_id"),
        ("AI_DISTRO_GOOGLE_CLIENT_SECRET", "client_secret"),
        ("AI_DISTRO_GOOGLE_REFRESH_TOKEN", "refresh_token"),
        ("AI_DISTRO_GOOGLE_CALENDAR_ID", "calendar_id"),
    ):
        val = os.environ.get(env_key, "").strip()
        if val:
            cfg[dst] = val
    if "calendar_id" not in cfg or not str(cfg.get("calendar_id", "")).strip():
        cfg["calendar_id"] = "primary"
    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not str(cfg.get(k, "")).strip()]
    if missing:
        return None
    return cfg


def google_access_token(cfg):
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
    token = str(payload.get("access_token", "")).strip()
    if not token:
        return None
    return token


def load_google_calendar_events(day: dt.date):
    cfg = load_google_oauth()
    if not cfg:
        return None
    try:
        token = google_access_token(cfg)
        if not token:
            return None
        day_start = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)
        day_end = day_start + dt.timedelta(days=1)
        params = urllib.parse.urlencode(
            {
                "singleEvents": "true",
                "orderBy": "startTime",
                "timeMin": _iso_utc(day_start),
                "timeMax": _iso_utc(day_end),
                "maxResults": "20",
            }
        )
        cal_id = urllib.parse.quote(str(cfg.get("calendar_id", "primary")), safe="")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events?{params}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None

    items = payload.get("items", [])
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary", "event")).strip() or "event"
        start = item.get("start", {})
        if not isinstance(start, dict):
            start = {}
        start_raw = str(start.get("dateTime") or start.get("date") or "").strip()
        text = f"{summary} {item.get('location', '')}".lower()
        dress = "casual"
        if any(k in text for k in ("interview", "wedding", "ceremony", "formal")):
            dress = "formal"
        elif any(k in text for k in ("meeting", "office", "client", "work")):
            dress = "business"
        outdoor = any(k in text for k in ("park", "run", "hike", "walk", "outdoor", "soccer", "football"))
        out.append(
            {
                "title": summary,
                "start": start_raw,
                "outdoor": outdoor,
                "dress_code": dress,
            }
        )
    return out


def load_microsoft_oauth():
    cfg_path = os.environ.get(
        "AI_DISTRO_MICROSOFT_OUTLOOK_OAUTH_FILE",
        os.path.expanduser("~/.config/ai-distro/microsoft-outlook-oauth.json"),
    )
    cfg = {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
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

    if "tenant_id" not in cfg or not str(cfg.get("tenant_id", "")).strip():
        cfg["tenant_id"] = "common"
    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not str(cfg.get(k, "")).strip()]
    if missing:
        return None
    return cfg


def microsoft_access_token(cfg):
    scope = os.environ.get(
        "AI_DISTRO_MICROSOFT_CALENDAR_SCOPE",
        "offline_access https://graph.microsoft.com/Calendars.Read",
    ).strip()
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
    if not token:
        return None
    return token


def load_microsoft_calendar_events(day: dt.date):
    cfg = load_microsoft_oauth()
    if not cfg:
        return None
    try:
        token = microsoft_access_token(cfg)
        if not token:
            return None
        day_start = dt.datetime.combine(day, dt.time.min)
        day_end = day_start + dt.timedelta(days=1)
        params = urllib.parse.urlencode(
            {
                "startDateTime": day_start.isoformat(),
                "endDateTime": day_end.isoformat(),
                "$orderby": "start/dateTime",
                "$top": "20",
            }
        )
        url = f"https://graph.microsoft.com/v1.0/me/calendarView?{params}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None

    items = payload.get("value", [])
    if not isinstance(items, list):
        return []

    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        summary = str(item.get("subject", "event")).strip() or "event"
        start = item.get("start", {})
        if not isinstance(start, dict):
            start = {}
        start_raw = str(start.get("dateTime") or "").strip()
        location = item.get("location", {})
        location_text = ""
        if isinstance(location, dict):
            location_text = str(location.get("displayName", "")).strip()
        text = f"{summary} {location_text}".lower()
        dress = "casual"
        if any(k in text for k in ("interview", "wedding", "ceremony", "formal")):
            dress = "formal"
        elif any(k in text for k in ("meeting", "office", "client", "work")):
            dress = "business"
        outdoor = any(k in text for k in ("park", "run", "hike", "walk", "outdoor", "soccer", "football"))
        out.append(
            {
                "title": summary,
                "start": start_raw,
                "outdoor": outdoor,
                "dress_code": dress,
            }
        )
    return out


def fetch_weather(day: dt.date):
    location = os.environ.get("AI_DISTRO_WEATHER_LOCATION", "Austin").strip() or "Austin"
    encoded_loc = urllib.parse.quote(location)
    url = f"https://wttr.in/{encoded_loc}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "ai-distro-agent/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None

    days = payload.get("weather", [])
    idx = 0 if day == dt.date.today() else 1
    if not isinstance(days, list) or len(days) <= idx:
        return None

    selected = days[idx]
    try:
        temp_min = int(selected.get("mintempC", "0"))
        temp_max = int(selected.get("maxtempC", "0"))
        hourly = selected.get("hourly", [])
        rain = 0
        if isinstance(hourly, list) and hourly:
            rain = max(int(h.get("chanceofrain", "0")) for h in hourly if isinstance(h, dict))
    except Exception:
        return None

    return {
        "location": location,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "rain_chance": rain,
    }


def clothing_rules(forecast, events):
    tips = []
    if forecast:
        tmin = forecast["temp_min"]
        tmax = forecast["temp_max"]
        rain = forecast["rain_chance"]
        if tmax >= 30:
            tips.append("light, breathable layers")
        elif tmax <= 12:
            tips.append("a warm jacket")
        else:
            tips.append("medium layers")
        if tmin <= 8:
            tips.append("closed shoes")
        if rain >= 40:
            tips.append("a rain layer or umbrella")

    dress_codes = {e.get("dress_code", "casual") for e in events}
    if "formal" in dress_codes:
        tips.append("formal attire")
    elif "business" in dress_codes:
        tips.append("business-casual pieces")

    if any(e.get("outdoor") for e in events):
        tips.append("comfortable walking shoes")

    if not tips:
        tips.append("casual comfortable clothes")

    # Keep output compact and stable.
    deduped = []
    for tip in tips:
        if tip not in deduped:
            deduped.append(tip)
    return deduped[:4]


def build_message(day, forecast, events, tips):
    day_label = "today" if day == dt.date.today() else "tomorrow"
    weather_part = "weather unavailable"
    if forecast:
        weather_part = (
            f"{forecast['location']} forecast {day_label}: "
            f"{forecast['temp_min']}C to {forecast['temp_max']}C, "
            f"rain chance {forecast['rain_chance']}%"
        )
    event_part = "no calendar events found"
    if events:
        names = ", ".join(e["title"] for e in events[:3])
        event_part = f"{len(events)} event(s): {names}"
    tips_part = "; ".join(tips)
    return f"{weather_part}. {event_part}. Clothing recommendation: {tips_part}."


def main():
    payload = "today"
    if len(sys.argv) > 1:
        payload = " ".join(sys.argv[1:])
    day = target_date(payload)
    provider = load_providers().get("calendar", "local")
    events = None
    if provider == "google":
        events = load_google_calendar_events(day)
    elif provider == "microsoft":
        events = load_microsoft_calendar_events(day)
    if events is None:
        events = load_calendar_events(day)
    forecast = fetch_weather(day)
    tips = clothing_rules(forecast, events)
    msg = build_message(day, forecast, events, tips)
    print(msg)


if __name__ == "__main__":
    main()
