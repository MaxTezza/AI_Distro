#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.parse

DEFAULT_MAP = "/etc/ai-distro/intent-map.json"


def load_intent_map():
    path = os.environ.get("AI_DISTRO_INTENT_MAP", DEFAULT_MAP)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def to_action(name, payload=None):
    action = {"version": 1, "name": name}
    if payload is not None:
        action["payload"] = payload
    return action


def normalize(text):
    return re.sub(r"\s+", " ", text.strip().lower())


def parse_install(text):
    match = re.search(r"\binstall\b(.+)", text)
    if not match:
        return None
    pkgs = match.group(1)
    pkgs = re.sub(r"\b(and|,|please)\b", " ", pkgs)
    pkgs = ",".join([p for p in pkgs.split() if p])
    return pkgs if pkgs else None


def parse_percent(text, keyword):
    match = re.search(rf"{keyword}[^0-9]*(\d{{1,3}})", text)
    if not match:
        return None
    return match.group(1)


def parse_url(text):
    if re.search(r"\b(gmail|g-mail|g mail)\b", text):
        return "https://mail.google.com/"
    match = re.search(r"\b(go to|open|visit)\b\s+(.+)$", text)
    if not match:
        return None
    dest = match.group(2).strip()
    if " " in dest:
        return None
    if not re.match(r"^https?://", dest):
        dest = "https://" + dest
    return dest


def parse_search(text):
    match = re.search(r"\b(search for|google)\b\s+(.+)$", text)
    if not match:
        return None
    query = match.group(2).strip()
    if not query:
        return None
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def parse_open_app(text):
    match = re.search(r"\b(open|launch|start)\b\s+(.+)$", text)
    if not match:
        return None
    app = match.group(2).strip()
    if not app:
        return None
    if "gmail" in app:
        return None
    if "http" in app or "." in app:
        return None
    return app


def parse_remember(text):
    match = re.search(r"\bremember\b\s+that\s+(.+)$", text)
    if not match:
        return None
    return match.group(1).strip()


def main():
    if len(sys.argv) < 2:
        print(json.dumps(to_action("unknown", "")))
        return

    raw = " ".join(sys.argv[1:])
    text = normalize(raw)

    if "check my gmail" in text or "open gmail" in text:
        print(json.dumps(to_action("open_url", "https://mail.google.com/")))
        return

    remember = parse_remember(text)
    if remember:
        print(json.dumps(to_action("remember", remember)))
        return

    if "wifi" in text and "on" in text:
        print(json.dumps(to_action("network_wifi_on")))
        return
    if "wifi" in text and "off" in text:
        print(json.dumps(to_action("network_wifi_off")))
        return
    if "bluetooth" in text and "on" in text:
        print(json.dumps(to_action("network_bluetooth_on")))
        return
    if "bluetooth" in text and "off" in text:
        print(json.dumps(to_action("network_bluetooth_off")))
        return

    if any(word in text for word in ["restart", "reboot"]):
        print(json.dumps(to_action("power_reboot")))
        return
    if any(word in text for word in ["shutdown", "power off"]):
        print(json.dumps(to_action("power_shutdown")))
        return
    if "sleep" in text:
        print(json.dumps(to_action("power_sleep")))
        return

    volume = parse_percent(text, "volume")
    if volume:
        print(json.dumps(to_action("set_volume", volume)))
        return
    brightness = parse_percent(text, "brightness")
    if brightness:
        print(json.dumps(to_action("set_brightness", brightness)))
        return

    if "update" in text and "system" in text:
        print(json.dumps(to_action("system_update", "stable")))
        return

    install = parse_install(text)
    if install:
        print(json.dumps(to_action("package_install", install)))
        return

    search_url = parse_search(text)
    if search_url:
        print(json.dumps(to_action("open_url", search_url)))
        return

    url = parse_url(text)
    if url:
        print(json.dumps(to_action("open_url", url)))
        return

    app = parse_open_app(text)
    if app:
        print(json.dumps(to_action("open_app", app)))
        return

    # Fallback: try intent map examples
    intent_map = load_intent_map()
    for name, entry in intent_map.items():
        for example in entry.get("examples", []):
            if normalize(example) in text:
                payload_key = entry.get("payload")
                if payload_key:
                    print(json.dumps(to_action(name, text)))
                else:
                    print(json.dumps(to_action(name)))
                return

    print(json.dumps(to_action("unknown", raw)))


if __name__ == "__main__":
    main()
