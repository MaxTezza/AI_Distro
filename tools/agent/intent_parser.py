#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.parse

DEFAULT_MAP = "/etc/ai-distro/intent-map.json"
HOME_DIR = os.environ.get("HOME", "/home/casper")


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


def resolve_user_path(raw):
    path = raw.strip().strip("\"'")
    if path in ("", ".", "here"):
        return "."
    if path in ("home", "my home", "~"):
        return HOME_DIR
    aliases = {
        "desktop": "Desktop",
        "documents": "Documents",
        "downloads": "Downloads",
        "music": "Music",
        "pictures": "Pictures",
        "videos": "Videos",
    }
    if path in aliases:
        return os.path.join(HOME_DIR, aliases[path])
    if path.startswith("~/"):
        return os.path.join(HOME_DIR, path[2:])
    return path


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


def parse_list_files(text):
    match = re.search(r"\b(list|show)\s+(my\s+)?files(?:\s+(in|from)\s+(.+))?$", text)
    if match:
        raw_path = (match.group(4) or "home").strip()
        return resolve_user_path(raw_path)

    match = re.search(r"\bwhat files are in\s+(.+)$", text)
    if match:
        return resolve_user_path(match.group(1))

    return None


def parse_read_context(text):
    prompts = (
        "what do you remember",
        "what did i ask you to remember",
        "show my notes",
        "recall my notes",
        "read my context",
    )
    if text in prompts:
        return "default"
    return None


def parse_url(text):
    if re.search(r"\b(gmail|g-mail|g mail)\b", text):
        return "https://mail.google.com/"
    match = re.search(r"\b(go to|open|visit)\b\s+(.+)$", text)
    if not match:
        return None
    verb = match.group(1)
    dest = match.group(2).strip()
    if " " in dest:
        return None
    # "open firefox" should map to open_app, not URL.
    if verb == "open" and not re.search(r"[./:]", dest):
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
    match = re.search(r"\bremember\b(?:\s+that)?\s+(.+)$", text)
    if not match:
        return None
    return match.group(1).strip()


def parse_outfit_planner(text):
    prompts = (
        "what should i wear",
        "what should i wear today",
        "what should i wear tomorrow",
        "what should i wear for today",
        "what should i wear for tomorrow",
        "what should i wear based on my calendar",
        "outfit recommendation",
        "give me an outfit recommendation",
        "clothing recommendation",
    )
    if text in prompts:
        if "tomorrow" in text:
            return "tomorrow"
        return "today"
    if "what should i wear" in text:
        return "tomorrow" if "tomorrow" in text else "today"
    if "outfit" in text and "recommend" in text:
        return "tomorrow" if "tomorrow" in text else "today"
    if "clothing" in text and "recommend" in text:
        return "tomorrow" if "tomorrow" in text else "today"
    return None


def parse_weather(text):
    prompts = (
        "what is the weather",
        "weather today",
        "weather tomorrow",
        "forecast today",
        "forecast tomorrow",
    )
    if text in prompts:
        return "tomorrow" if "tomorrow" in text else "today"
    if text.startswith("weather ") or text.startswith("forecast "):
        return "tomorrow" if "tomorrow" in text else "today"
    if text.startswith("what is the weather"):
        return "tomorrow" if "tomorrow" in text else "today"
    return None


def parse_calendar_list(text):
    prompts = (
        "what is on my calendar",
        "what is on my calendar today",
        "what is on my calendar tomorrow",
        "list calendar events",
        "list calendar events today",
        "list calendar events tomorrow",
    )
    if text in prompts or "calendar" in text and ("what is on" in text or "list" in text):
        return "tomorrow" if "tomorrow" in text else "today"
    return None


def parse_calendar_add(text):
    # Examples:
    # "add calendar event tomorrow at 3pm dentist appointment"
    # "schedule today at 14:30 team sync"
    m = re.search(r"\b(add|schedule)\b(?:\s+calendar(?:\s+event)?)?\s+(today|tomorrow)?\s*(?:at\s+([0-9:apm\s]+))?\s+(.+)$", text)
    if not m:
        return None
    day = (m.group(2) or "today").strip().lower()
    time_part = (m.group(3) or "09:00").strip().lower()
    title = (m.group(4) or "").strip()
    if not title:
        return None
    dress = "casual"
    if any(k in title.lower() for k in ("meeting", "office", "client", "work")):
        dress = "business"
    if any(k in title.lower() for k in ("interview", "wedding", "formal", "ceremony")):
        dress = "formal"
    outdoor = "true" if any(k in title.lower() for k in ("walk", "run", "hike", "outdoor", "park")) else "false"
    return f"{day}|{time_part}|{title}|{dress}|{outdoor}"


def parse_email_summary(text):
    prompts = (
        "summarize my email",
        "summarize my inbox",
        "email summary",
        "inbox summary",
    )
    if text in prompts:
        return "in:inbox newer_than:2d"
    return None


def parse_email_search(text):
    # "search my email for invoices"
    m = re.search(r"\bsearch\b(?:\s+my)?\s+(?:email|inbox)\s+(?:for|about)\s+(.+)$", text)
    if m:
        query = m.group(1).strip()
        if query:
            return query
    return None


def parse_email_draft(text):
    # draft email to someone@example.com about subject body text...
    m = re.search(r"\b(?:draft|write)\s+(?:an\s+)?email\s+to\s+(\S+)\s+about\s+(.+)$", text)
    if not m:
        return None
    to = m.group(1).strip().strip(".,")
    rest = m.group(2).strip()
    if not to or not rest:
        return None
    if " body " in rest:
        subj, body = rest.split(" body ", 1)
    else:
        subj = rest
        body = f"Hi,\n\n{rest}\n\nThanks."
    subj = subj.strip()
    body = body.strip()
    if not subj:
        return None
    return f"{to}|{subj}|{body}"


def main():
    if len(sys.argv) < 2:
        print(json.dumps(to_action("unknown", "")))
        return

    raw = " ".join(sys.argv[1:])
    text = normalize(raw)

    if text in ("help", "what can you do", "what can i say", "show commands"):
        print(json.dumps(to_action("get_capabilities")))
        return

    if text in ("are you there", "hello", "hello assistant", "ping"):
        print(json.dumps(to_action("ping")))
        return

    if "check my gmail" in text or "open gmail" in text:
        print(json.dumps(to_action("open_url", "https://mail.google.com/")))
        return

    read_context = parse_read_context(text)
    if read_context:
        print(json.dumps(to_action("read_context", read_context)))
        return

    remember = parse_remember(text)
    if remember:
        print(json.dumps(to_action("remember", remember)))
        return

    outfit = parse_outfit_planner(text)
    if outfit:
        print(json.dumps(to_action("plan_day_outfit", outfit)))
        return

    weather = parse_weather(text)
    if weather:
        print(json.dumps(to_action("weather_get", weather)))
        return

    calendar_add = parse_calendar_add(text)
    if calendar_add:
        print(json.dumps(to_action("calendar_add_event", calendar_add)))
        return

    calendar_list = parse_calendar_list(text)
    if calendar_list:
        print(json.dumps(to_action("calendar_list_day", calendar_list)))
        return

    email_summary = parse_email_summary(text)
    if email_summary:
        print(json.dumps(to_action("email_inbox_summary", email_summary)))
        return

    email_query = parse_email_search(text)
    if email_query:
        print(json.dumps(to_action("email_search", email_query)))
        return

    email_draft = parse_email_draft(text)
    if email_draft:
        print(json.dumps(to_action("email_draft", email_draft)))
        return

    files_path = parse_list_files(text)
    if files_path:
        print(json.dumps(to_action("list_files", files_path)))
        return

    if "wifi" in text and "on" in text:
        print(json.dumps(to_action("network_wifi_on")))
        return
    if "wifi" in text and ("off" in text or "disable" in text):
        print(json.dumps(to_action("network_wifi_off")))
        return
    if "wifi" in text and "enable" in text:
        print(json.dumps(to_action("network_wifi_on")))
        return
    if "bluetooth" in text and ("on" in text or "enable" in text):
        print(json.dumps(to_action("network_bluetooth_on")))
        return
    if "bluetooth" in text and ("off" in text or "disable" in text):
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

    if "update" in text or "upgrade" in text:
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
            if normalize(example) == text:
                print(json.dumps(to_action(name)))
                return

    print(json.dumps(to_action("unknown", raw)))


if __name__ == "__main__":
    main()
