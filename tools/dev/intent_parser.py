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
