#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse
import urllib.request


def oauth_config():
    path = os.environ.get(
        "AI_DISTRO_GOOGLE_GMAIL_OAUTH_FILE",
        os.path.expanduser("~/.config/ai-distro/google-gmail-oauth.json"),
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
        ("AI_DISTRO_GOOGLE_GMAIL_REFRESH_TOKEN", "refresh_token"),
    ):
        val = os.environ.get(env_key, "").strip()
        if val:
            cfg[dst] = val
    if not str(cfg.get("refresh_token", "")).strip():
        # fallback to generic google refresh token if present
        rt = os.environ.get("AI_DISTRO_GOOGLE_REFRESH_TOKEN", "").strip()
        if rt:
            cfg["refresh_token"] = rt

    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not str(cfg.get(k, "")).strip()]
    if missing:
        return None
    return cfg


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
    token = str(payload.get("access_token", "")).strip()
    return token or None


def gmail_request(token, url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def message_overview(token, msg_id):
    url = (
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/"
        f"{urllib.parse.quote(msg_id, safe='')}?format=metadata"
        "&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"
    )
    payload = gmail_request(token, url)
    headers = payload.get("payload", {}).get("headers", [])
    hdr = {h.get("name", "").lower(): h.get("value", "") for h in headers if isinstance(h, dict)}
    return {
        "from": hdr.get("from", "").strip(),
        "subject": hdr.get("subject", "").strip() or "(no subject)",
        "date": hdr.get("date", "").strip(),
        "snippet": str(payload.get("snippet", "")).strip(),
    }


def list_messages(token, query, max_results=5):
    params = urllib.parse.urlencode({"q": query, "maxResults": str(max_results)})
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?{params}"
    payload = gmail_request(token, url)
    msgs = payload.get("messages", [])
    out = []
    if not isinstance(msgs, list):
        return out
    for m in msgs[:max_results]:
        if not isinstance(m, dict):
            continue
        msg_id = str(m.get("id", "")).strip()
        if not msg_id:
            continue
        try:
            out.append(message_overview(token, msg_id))
        except Exception:
            continue
    return out


def format_summary(items, title):
    if not items:
        return f"{title}: no matching emails."
    lines = [f"{title}: {len(items)} message(s)."]
    for it in items:
        sender = it.get("from", "unknown sender")
        subject = it.get("subject", "(no subject)")
        lines.append(f"- {subject} ({sender})")
    return "\n".join(lines)


def cmd_summary(token, query):
    q = query.strip() if query.strip() else "in:inbox newer_than:2d"
    items = list_messages(token, q, 5)
    return format_summary(items, "Inbox summary")


def cmd_search(token, query):
    q = query.strip() if query.strip() else "in:inbox"
    items = list_messages(token, q, 5)
    return format_summary(items, f"Email search '{q}'")


def main():
    if len(sys.argv) < 2:
        print("usage: gmail_tool.py summary|search [query]")
        return 2
    cfg = oauth_config()
    if not cfg:
        print("Gmail OAuth not configured.")
        return 0
    try:
        token = access_token(cfg)
        if not token:
            print("Unable to acquire Gmail access token.")
            return 0
    except Exception:
        print("Unable to acquire Gmail access token.")
        return 0

    cmd = sys.argv[1].strip().lower()
    query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    try:
        if cmd == "summary":
            print(cmd_summary(token, query))
            return 0
        if cmd == "search":
            print(cmd_search(token, query))
            return 0
    except Exception:
        print("Gmail request failed.")
        return 0
    print("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

