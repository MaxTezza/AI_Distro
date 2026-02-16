#!/usr/bin/env python3
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def target_day(payload: str) -> str:
    p = (payload or "today").strip().lower()
    if "tomorrow" in p:
        return "tomorrow"
    return "today"


def fetch_forecast(day_label: str):
    location = os.environ.get("AI_DISTRO_WEATHER_LOCATION", "Austin").strip() or "Austin"
    encoded = urllib.parse.quote(location)
    req = urllib.request.Request(
        f"https://wttr.in/{encoded}?format=j1",
        headers={"User-Agent": "ai-distro-agent/0.1"},
    )
    with urllib.request.urlopen(req, timeout=6.0) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    weather = payload.get("weather", [])
    idx = 0 if day_label == "today" else 1
    if not isinstance(weather, list) or len(weather) <= idx:
        return None
    day = weather[idx]
    hourly = day.get("hourly", [])
    rain = 0
    if isinstance(hourly, list) and hourly:
        for entry in hourly:
            if isinstance(entry, dict):
                try:
                    rain = max(rain, int(entry.get("chanceofrain", "0")))
                except Exception:
                    continue
    try:
        return {
            "location": location,
            "min_c": int(day.get("mintempC", "0")),
            "max_c": int(day.get("maxtempC", "0")),
            "rain": rain,
        }
    except Exception:
        return None


def main():
    payload = "today" if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    day_label = target_day(payload)
    try:
        forecast = fetch_forecast(day_label)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        forecast = None
    if not forecast:
        print(f"Weather unavailable for {day_label}.")
        return
    print(
        f"{forecast['location']} {day_label}: "
        f"{forecast['min_c']}C to {forecast['max_c']}C, "
        f"rain chance up to {forecast['rain']}%."
    )


if __name__ == "__main__":
    main()

