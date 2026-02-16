#!/usr/bin/env python3
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


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
    events = load_calendar_events(day)
    forecast = fetch_weather(day)
    tips = clothing_rules(forecast, events)
    msg = build_message(day, forecast, events, tips)
    print(msg)


if __name__ == "__main__":
    main()

