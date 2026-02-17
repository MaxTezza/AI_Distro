#!/usr/bin/env python3
import json
import os
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


def access_token(cfg):
    scope = os.environ.get(
        "AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE",
        "offline_access https://graph.microsoft.com/Mail.Read",
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
    return token or None


def graph_get(token, url, extra_headers=None):
    headers = {"Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def format_items(items, title):
    if not items:
        return f"{title}: no matching emails."
    lines = [f"{title}: {len(items)} message(s)."]
    for it in items:
        subject = str(it.get("subject", "")).strip() or "(no subject)"
        sender = (
            ((it.get("from") or {}).get("emailAddress") or {}).get("address")
            if isinstance(it.get("from"), dict)
            else ""
        )
        sender = str(sender or "").strip() or "unknown sender"
        lines.append(f"- {subject} ({sender})")
    return "\n".join(lines)


def cmd_summary(token):
    params = urllib.parse.urlencode(
        {
            "$top": "5",
            "$orderby": "receivedDateTime DESC",
            "$select": "subject,from,receivedDateTime,bodyPreview",
        }
    )
    url = f"https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?{params}"
    payload = graph_get(token, url)
    items = payload.get("value", [])
    if not isinstance(items, list):
        items = []
    return format_items(items[:5], "Inbox summary")


def cmd_search(token, query):
    q = (query or "").strip()
    if not q:
        return cmd_summary(token)
    escaped = q.replace('"', "")
    params = urllib.parse.urlencode(
        {
            "$top": "5",
            "$search": f"\"{escaped}\"",
            "$select": "subject,from,receivedDateTime,bodyPreview",
        }
    )
    url = f"https://graph.microsoft.com/v1.0/me/messages?{params}"
    payload = graph_get(token, url, {"ConsistencyLevel": "eventual"})
    items = payload.get("value", [])
    if not isinstance(items, list):
        items = []
    return format_items(items[:5], f"Email search '{q}'")


def main():
    if len(sys.argv) < 2:
        print("usage: outlook_tool.py summary|search|draft [query]")
        return 2
    cmd = sys.argv[1].strip().lower()
    query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    if cmd == "draft":
        print("Outlook draft is not enabled yet.")
        return 0

    cfg = oauth_config()
    if not cfg:
        print("Outlook OAuth not configured.")
        return 0
    try:
        token = access_token(cfg)
        if not token:
            print("Unable to acquire Outlook access token.")
            return 0
    except Exception:
        print("Unable to acquire Outlook access token.")
        return 0

    try:
        if cmd == "summary":
            print(cmd_summary(token))
            return 0
        if cmd == "search":
            print(cmd_search(token, query))
            return 0
    except Exception:
        print("Outlook request failed.")
        return 0
    print("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

