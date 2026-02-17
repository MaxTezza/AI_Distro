#!/usr/bin/env python3
import datetime as dt
import email
import imaplib
import os
import re
import sys
from email.header import decode_header


def cfg():
    return {
        "host": os.environ.get("AI_DISTRO_IMAP_HOST", "").strip(),
        "port": int(os.environ.get("AI_DISTRO_IMAP_PORT", "993")),
        "username": os.environ.get("AI_DISTRO_IMAP_USERNAME", "").strip(),
        "password": os.environ.get("AI_DISTRO_IMAP_PASSWORD", "").strip(),
        "folder": os.environ.get("AI_DISTRO_IMAP_FOLDER", "INBOX").strip() or "INBOX",
        "tls_mode": os.environ.get("AI_DISTRO_IMAP_TLS_MODE", "ssl").strip().lower(),
    }


def decode_mime(value):
    if not value:
        return ""
    out = []
    for part, enc in decode_header(value):
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="ignore"))
        else:
            out.append(str(part))
    return "".join(out).strip()


def connect(c):
    if c["tls_mode"] == "starttls":
        m = imaplib.IMAP4(c["host"], c["port"])
        m.starttls()
    else:
        m = imaplib.IMAP4_SSL(c["host"], c["port"])
    m.login(c["username"], c["password"])
    return m


def fetch_headers(m, msg_id):
    typ, data = m.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
    if typ != "OK" or not data:
        return None
    raw = b""
    for chunk in data:
        if isinstance(chunk, tuple) and len(chunk) > 1 and isinstance(chunk[1], bytes):
            raw += chunk[1]
    if not raw:
        return None
    msg = email.message_from_bytes(raw)
    return {
        "subject": decode_mime(msg.get("Subject", "")) or "(no subject)",
        "from": decode_mime(msg.get("From", "")) or "unknown sender",
        "date": decode_mime(msg.get("Date", "")),
    }


def format_lines(items, title):
    if not items:
        return f"{title}: no matching emails."
    lines = [f"{title}: {len(items)} message(s)."]
    for it in items:
        lines.append(f"- {it['subject']} ({it['from']})")
    return "\n".join(lines)


def cmd_summary(m, folder):
    m.select(folder, readonly=True)
    since = (dt.date.today() - dt.timedelta(days=2)).strftime("%d-%b-%Y")
    typ, data = m.search(None, "SINCE", since)
    if typ != "OK":
        return "Inbox summary: unable to read mailbox."
    ids = data[0].split()[-5:]
    rows = []
    for mid in reversed(ids):
        row = fetch_headers(m, mid)
        if row:
            rows.append(row)
    return format_lines(rows, "Inbox summary")


def cmd_search(m, folder, query):
    m.select(folder, readonly=True)
    q = (query or "").strip()
    if not q:
        return cmd_summary(m, folder)
    # IMAP SEARCH TEXT is broad and server-supported in most deployments.
    typ, data = m.search(None, "TEXT", f'"{q}"')
    if typ != "OK":
        return f"Email search '{q}': unable to query mailbox."
    ids = data[0].split()[-5:]
    rows = []
    for mid in reversed(ids):
        row = fetch_headers(m, mid)
        if row:
            rows.append(row)
    return format_lines(rows, f"Email search '{q}'")


def main():
    if len(sys.argv) < 2:
        print("usage: email_imap_tool.py summary|search|draft [query]")
        return 2
    cmd = sys.argv[1].strip().lower()
    query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    if cmd == "draft":
        print("IMAP draft is not enabled yet.")
        return 0

    c = cfg()
    if not c["host"] or not c["username"] or not c["password"]:
        print("IMAP is not configured.")
        return 0

    try:
        m = connect(c)
    except Exception:
        print("Unable to connect to IMAP server.")
        return 0

    try:
        if cmd == "summary":
            print(cmd_summary(m, c["folder"]))
            return 0
        if cmd == "search":
            print(cmd_search(m, c["folder"], query))
            return 0
    except Exception:
        print("IMAP request failed.")
        return 0
    finally:
        try:
            m.logout()
        except Exception:
            pass

    print("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

