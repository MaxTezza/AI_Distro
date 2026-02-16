#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

MAP_PATH = Path(__file__).resolve().parents[2] / "configs" / "intent-map.json"


def load_map():
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def parse_intent(text: str, mapping: dict):
    text_n = normalize(text)

    # simple keyword-based matching with examples
    for intent, spec in mapping.items():
        for ex in spec.get("examples", []):
            if normalize(ex) == text_n:
                return intent, extract_payload(intent, text_n)

    # fallback keyword heuristics
    if text_n.startswith("remember ") or text_n.startswith("note "):
        payload = extract_payload("remember", text_n)
        if payload:
            return "remember", payload

    if text_n.startswith("remember that "):
        payload = extract_payload("remember", text_n)
        if payload:
            return "remember", payload

    if text_n.startswith("list files"):
        payload = extract_payload("list_files", text_n)
        return "list_files", payload

    if "what should i wear" in text_n or ("outfit" in text_n and "recommend" in text_n):
        payload = "tomorrow" if "tomorrow" in text_n else "today"
        return "plan_day_outfit", payload

    if (
        text_n.startswith("weather ")
        or text_n.startswith("forecast ")
        or text_n.startswith("what is the weather")
    ):
        payload = "tomorrow" if "tomorrow" in text_n else "today"
        return "weather_get", payload

    if "calendar" in text_n and ("what is on" in text_n or "list" in text_n):
        payload = "tomorrow" if "tomorrow" in text_n else "today"
        return "calendar_list_day", payload

    if text_n.startswith("add calendar event") or text_n.startswith("schedule "):
        payload = extract_payload("calendar_add_event", text_n)
        if payload:
            return "calendar_add_event", payload

    url_payload = extract_payload("open_url", text_n)
    if url_payload:
        return "open_url", url_payload

    if text_n.startswith("open ") or text_n.startswith("launch "):
        payload = extract_payload("open_app", text_n)
        if payload:
            return "open_app", payload

    if text_n.startswith("install ") or text_n.startswith("add "):
        payload = extract_payload("package_install", text_n)
        return "package_install", payload

    if "update" in text_n or "upgrade" in text_n:
        return "system_update", "stable"

    if "wifi" in text_n or "wireless" in text_n:
        if "off" in text_n or "disable" in text_n:
            return "network_wifi_off", None
        if "on" in text_n or "enable" in text_n:
            return "network_wifi_on", None

    if "bluetooth" in text_n:
        if "off" in text_n or "disable" in text_n:
            return "network_bluetooth_off", None
        if "on" in text_n or "enable" in text_n:
            return "network_bluetooth_on", None

    if "volume" in text_n:
        m = re.search(r"(\d+)", text_n)
        if m:
            return "set_volume", m.group(1)

    if "brightness" in text_n:
        m = re.search(r"(\d+)", text_n)
        if m:
            return "set_brightness", m.group(1)

    if "reboot" in text_n or "restart" in text_n:
        return "power_reboot", None

    if "shutdown" in text_n or "power off" in text_n:
        return "power_shutdown", None

    return None, None


def extract_payload(intent: str, text_n: str):
    if intent == "remember":
        for prefix in ("remember that ", "remember ", "note "):
            if text_n.startswith(prefix):
                payload = text_n[len(prefix):].strip()
                return payload if payload else None
        return None

    if intent == "list_files":
        m = re.search(r"(?:in|from)\s+(.+)$", text_n)
        if m:
            return m.group(1).strip()
        return "."

    if intent == "open_url":
        m = re.search(r"\bhttps?://\S+\b", text_n)
        if m:
            return m.group(0)
        m = re.search(r"\b(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+\b", text_n)
        if m:
            host = m.group(0)
            if not host.startswith(("http://", "https://")):
                host = f"https://{host}"
            return host
        for prefix in ("go to ", "open site ", "open website "):
            if text_n.startswith(prefix):
                tail = text_n[len(prefix):].strip()
                if tail:
                    if not re.match(r"^https?://", tail):
                        tail = f"https://{tail}"
                    return tail
        return None

    if intent == "open_app":
        for prefix in ("open ", "launch "):
            if text_n.startswith(prefix):
                payload = text_n[len(prefix):].strip()
                return payload if payload else None
        return None

    if intent == "package_install":
        parts = text_n.split(" ", 1)
        if len(parts) < 2:
            return None
        raw = parts[1]
        # support "vim and curl", "vim, curl", "vim curl"
        raw = raw.replace(",", " ")
        raw = raw.replace(" and ", " ")
        pkgs = [p for p in raw.split(" ") if p]
        return ",".join(pkgs) if pkgs else None
    if intent in ("set_volume", "set_brightness"):
        m = re.search(r"(\d+)", text_n)
        return m.group(1) if m else None
    if intent == "plan_day_outfit":
        return "tomorrow" if "tomorrow" in text_n else "today"
    if intent == "weather_get":
        return "tomorrow" if "tomorrow" in text_n else "today"
    if intent == "calendar_list_day":
        return "tomorrow" if "tomorrow" in text_n else "today"
    if intent == "calendar_add_event":
        m = re.search(r"\b(?:add calendar event|schedule)\b\s+(today|tomorrow)?\s*(?:at\s+([0-9:apm\s]+))?\s+(.+)$", text_n)
        if not m:
            return None
        day = (m.group(1) or "today").strip()
        when = (m.group(2) or "09:00").strip()
        title = (m.group(3) or "").strip()
        if not title:
            return None
        dress = "casual"
        if any(k in title for k in ("meeting", "office", "client", "work")):
            dress = "business"
        if any(k in title for k in ("interview", "wedding", "formal", "ceremony")):
            dress = "formal"
        outdoor = "true" if any(k in title for k in ("walk", "run", "hike", "outdoor", "park")) else "false"
        return f"{day}|{when}|{title}|{dress}|{outdoor}"
    if intent == "system_update":
        return "stable"
    return None


def main():
    if len(sys.argv) < 2:
        print("usage: intent_parser.py 'install firefox'")
        sys.exit(1)

    mapping = load_map()
    text = " ".join(sys.argv[1:])
    intent, payload = parse_intent(text, mapping)

    if not intent:
        print("intent: <unknown>")
        sys.exit(2)

    out = {"intent": intent}
    if payload is not None:
        out["payload"] = payload
    print(json.dumps(out))


if __name__ == "__main__":
    main()
