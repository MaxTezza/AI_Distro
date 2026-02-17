#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse
import urllib.request

DEFAULT_REDIRECT_URI = "http://127.0.0.1:53682/callback"
DEFAULT_SCOPE = "offline_access https://graph.microsoft.com/Mail.Read"


def load_client():
    client_id = os.environ.get("AI_DISTRO_MICROSOFT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("AI_DISTRO_MICROSOFT_CLIENT_SECRET", "").strip()
    tenant_id = os.environ.get("AI_DISTRO_MICROSOFT_TENANT_ID", "common").strip() or "common"
    redirect_uri = os.environ.get("AI_DISTRO_MICROSOFT_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()
    if not client_id or not client_secret:
        print("Missing AI_DISTRO_MICROSOFT_CLIENT_ID / AI_DISTRO_MICROSOFT_CLIENT_SECRET", file=sys.stderr)
        return None
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "tenant_id": tenant_id,
        "redirect_uri": redirect_uri,
    }


def oauth_path():
    return os.environ.get(
        "AI_DISTRO_MICROSOFT_OUTLOOK_OAUTH_FILE",
        os.path.expanduser("~/.config/ai-distro/microsoft-outlook-oauth.json"),
    )


def cmd_auth_url():
    cfg = load_client()
    if not cfg:
        return 2
    scope = os.environ.get("AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE", DEFAULT_SCOPE).strip()
    query = {
        "client_id": cfg["client_id"],
        "response_type": "code",
        "redirect_uri": cfg["redirect_uri"],
        "response_mode": "query",
        "scope": scope,
        "prompt": "select_account",
    }
    state = os.environ.get("AI_DISTRO_OAUTH_STATE", "").strip()
    if state:
        query["state"] = state
    params = urllib.parse.urlencode(query)
    print("Open this URL, authorize, then run:")
    print("  microsoft_outlook_oauth.py exchange <code>")
    print()
    print(f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/authorize?{params}")
    return 0


def cmd_exchange(code: str):
    cfg = load_client()
    if not cfg:
        return 2
    scope = os.environ.get("AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE", DEFAULT_SCOPE).strip()
    token_url = f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token"
    body = urllib.parse.urlencode(
        {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "code": code,
            "redirect_uri": cfg["redirect_uri"],
            "grant_type": "authorization_code",
            "scope": scope,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as exc:
        print(f"Token exchange failed: {exc}", file=sys.stderr)
        return 1

    refresh_token = str(payload.get("refresh_token", "")).strip()
    if not refresh_token:
        print("No refresh_token returned. Re-run auth-url and grant consent.", file=sys.stderr)
        return 1

    out = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "tenant_id": cfg["tenant_id"],
        "refresh_token": refresh_token,
    }
    path = oauth_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"Wrote Outlook OAuth config to {path}")
    return 0


def main():
    if len(sys.argv) < 2:
        print("usage: microsoft_outlook_oauth.py auth-url|exchange <code>", file=sys.stderr)
        return 2
    cmd = sys.argv[1].strip().lower()
    if cmd == "auth-url":
        return cmd_auth_url()
    if cmd == "exchange":
        if len(sys.argv) < 3:
            print("usage: microsoft_outlook_oauth.py exchange <code>", file=sys.stderr)
            return 2
        return cmd_exchange(sys.argv[2].strip())
    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
