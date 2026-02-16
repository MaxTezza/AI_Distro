#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse
import urllib.request

DEFAULT_REDIRECT_URI = "http://127.0.0.1:53682/callback"
DEFAULT_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def load_client():
    client_id = os.environ.get("AI_DISTRO_GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("AI_DISTRO_GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = os.environ.get("AI_DISTRO_GOOGLE_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()
    if not client_id or not client_secret:
        print("Missing AI_DISTRO_GOOGLE_CLIENT_ID / AI_DISTRO_GOOGLE_CLIENT_SECRET", file=sys.stderr)
        return None
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


def oauth_path():
    return os.environ.get(
        "AI_DISTRO_GOOGLE_GMAIL_OAUTH_FILE",
        os.path.expanduser("~/.config/ai-distro/google-gmail-oauth.json"),
    )


def cmd_auth_url():
    cfg = load_client()
    if not cfg:
        return 2
    params = urllib.parse.urlencode(
        {
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "response_type": "code",
            "scope": DEFAULT_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    print("Open this URL, authorize, then run:")
    print("  google_gmail_oauth.py exchange <code>")
    print()
    print(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")
    return 0


def cmd_exchange(code: str):
    cfg = load_client()
    if not cfg:
        return 2
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": cfg["redirect_uri"],
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
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
        print("No refresh_token returned. Re-run auth-url and ensure consent prompt.", file=sys.stderr)
        return 1

    out = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": refresh_token,
    }
    path = oauth_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"Wrote Gmail OAuth config to {path}")
    return 0


def main():
    if len(sys.argv) < 2:
        print("usage: google_gmail_oauth.py auth-url|exchange <code>", file=sys.stderr)
        return 2
    cmd = sys.argv[1].strip().lower()
    if cmd == "auth-url":
        return cmd_auth_url()
    if cmd == "exchange":
        if len(sys.argv) < 3:
            print("usage: google_gmail_oauth.py exchange <code>", file=sys.stderr)
            return 2
        return cmd_exchange(sys.argv[2].strip())
    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

