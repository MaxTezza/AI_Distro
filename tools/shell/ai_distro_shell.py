#!/usr/bin/env python3
import json
import os
import socket
import subprocess
import time
import uuid
from collections import deque
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

DEFAULT_SOCKET = "/run/ai-distro/agent.sock"
DEFAULT_STATIC = "/usr/share/ai-distro/ui/shell"
DEFAULT_PERSONA = "/etc/ai-distro/persona.json"
DEFAULT_PERSONA_ALFRED = "/etc/ai-distro/persona.alfred.json"
DEFAULT_ONBOARDING = os.path.expanduser("~/.config/ai-distro/shell-onboarding.json")
DEFAULT_PROVIDERS = os.path.expanduser("~/.config/ai-distro/providers.json")
DEFAULT_AUDIT_LOG = "/var/log/ai-distro-agent/audit.jsonl"


def agent_request(payload: dict, timeout=4.0):
    socket_path = os.environ.get("AI_DISTRO_IPC_SOCKET", DEFAULT_SOCKET)
    data = (json.dumps(payload) + "\n").encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(socket_path)
        client.sendall(data)
        response = b""
        while not response.endswith(b"\n"):
            chunk = client.recv(4096)
            if not chunk:
                break
            response += chunk
        if not response:
            raise RuntimeError("empty response")
        return json.loads(response.decode("utf-8").strip())


class ShellHandler(SimpleHTTPRequestHandler):
    OAUTH_SESSIONS = {}

    def _load_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _fallback_path(self, filename):
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", ".."))
        candidate = os.path.join(repo_root, "configs", filename)
        if os.path.exists(candidate):
            return candidate
        return None

    def _agent_tool_path(self, filename):
        packaged = Path("/usr/lib/ai-distro") / filename
        if packaged.exists():
            return str(packaged)
        here = Path(__file__).resolve().parent
        repo_tool = here.parent / "agent" / filename
        if repo_tool.exists():
            return str(repo_tool)
        return str(packaged)

    def _server_base_url(self):
        host = os.environ.get("AI_DISTRO_SHELL_HOST", "127.0.0.1")
        port = int(os.environ.get("AI_DISTRO_SHELL_PORT", "17842"))
        return f"http://{host}:{port}"

    def _load_persona(self):
        path = os.environ.get("AI_DISTRO_PERSONA", DEFAULT_PERSONA)
        if os.path.exists(path):
            return self._load_json(path)
        fallback = self._fallback_path("persona.json")
        if fallback:
            return self._load_json(fallback)
        return {}

    def _load_persona_presets(self):
        presets = {}
        max_path = os.environ.get("AI_DISTRO_PERSONA", DEFAULT_PERSONA)
        if os.path.exists(max_path):
            presets["max"] = self._load_json(max_path)
        else:
            fallback = self._fallback_path("persona.json")
            if fallback:
                presets["max"] = self._load_json(fallback)

        alfred_path = DEFAULT_PERSONA_ALFRED
        if os.path.exists(alfred_path):
            presets["alfred"] = self._load_json(alfred_path)
        else:
            fallback = self._fallback_path("persona.alfred.json")
            if fallback:
                presets["alfred"] = self._load_json(fallback)
        return presets

    def _write_persona(self, preset_key):
        presets = self._load_persona_presets()
        if preset_key not in presets:
            return False, "unknown preset"
        path = os.environ.get("AI_DISTRO_PERSONA", DEFAULT_PERSONA)
        data = presets[preset_key]
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.write("\n")
            return True, path
        except Exception as exc:
            return False, str(exc)

    def _onboarding_path(self):
        return os.environ.get("AI_DISTRO_ONBOARDING_STATE", DEFAULT_ONBOARDING)

    def _load_onboarding(self):
        path = self._onboarding_path()
        if not os.path.exists(path):
            return {}
        return self._load_json(path)

    def _write_onboarding(self, state):
        path = self._onboarding_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2)
                fh.write("\n")
            return True, path
        except Exception as exc:
            return False, str(exc)

    def _providers_path(self):
        return os.environ.get("AI_DISTRO_PROVIDERS_FILE", DEFAULT_PROVIDERS)

    def _default_providers(self):
        return {"calendar": "local", "email": "gmail", "weather": "default"}

    def _load_providers(self):
        path = self._providers_path()
        providers = self._default_providers()
        if not os.path.exists(path):
            return providers
        payload = self._load_json(path)
        if isinstance(payload, dict):
            for key in ("calendar", "email", "weather"):
                val = payload.get(key)
                if isinstance(val, str) and val.strip():
                    providers[key] = val.strip().lower()
        return providers

    def _write_providers(self, providers):
        path = self._providers_path()
        data = self._default_providers()
        if isinstance(providers, dict):
            for key in ("calendar", "email", "weather"):
                val = providers.get(key)
                if isinstance(val, str) and val.strip():
                    data[key] = val.strip().lower()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.write("\n")
            return True, path
        except Exception as exc:
            return False, str(exc)

    def _extract_url(self, text):
        m = re.search(r"https://[^\s]+", text or "")
        return m.group(0) if m else ""

    def _audit_log_path(self):
        return os.environ.get("AI_DISTRO_AUDIT_LOG", DEFAULT_AUDIT_LOG)

    def _load_recent_task_events(self, limit=8):
        log_path = self._audit_log_path()
        if not os.path.exists(log_path):
            return []

        recent = deque(maxlen=max(1, min(int(limit), 30)))
        try:
            with open(log_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    if obj.get("type") != "action_outcome":
                        continue
                    action = str(obj.get("action", "")).strip()
                    if action not in ("package_install", "package_remove", "system_update"):
                        continue
                    status = str(obj.get("status", "")).strip().lower() or "unknown"
                    msg = str(obj.get("message", "")).strip() or "Task completed."
                    ts = obj.get("ts")
                    recent.append(
                        {
                            "ts": ts,
                            "action": action,
                            "status": status,
                            "message": msg,
                        }
                    )
        except Exception:
            return []

        out = list(recent)
        out.reverse()
        return out

    def _provider_env(self, provider, payload):
        env = os.environ.copy()
        client_id = str(payload.get("client_id", "")).strip()
        client_secret = str(payload.get("client_secret", "")).strip()
        redirect_uri = str(payload.get("redirect_uri", "")).strip()
        state = str(payload.get("state", "")).strip()
        if provider in ("google", "gmail"):
            if client_id:
                env["AI_DISTRO_GOOGLE_CLIENT_ID"] = client_id
            if client_secret:
                env["AI_DISTRO_GOOGLE_CLIENT_SECRET"] = client_secret
            if redirect_uri:
                env["AI_DISTRO_GOOGLE_REDIRECT_URI"] = redirect_uri
        if provider in ("microsoft", "outlook"):
            if client_id:
                env["AI_DISTRO_MICROSOFT_CLIENT_ID"] = client_id
            if client_secret:
                env["AI_DISTRO_MICROSOFT_CLIENT_SECRET"] = client_secret
            if redirect_uri:
                env["AI_DISTRO_MICROSOFT_REDIRECT_URI"] = redirect_uri
        if state:
            env["AI_DISTRO_OAUTH_STATE"] = state
        return env

    def _oauth_start(self, target, provider, payload):
        state = uuid.uuid4().hex
        callback_uri = f"{self._server_base_url()}/oauth/callback"
        session = {
            "target": target,
            "provider": provider,
            "client_id": str(payload.get("client_id", "")).strip(),
            "client_secret": str(payload.get("client_secret", "")).strip(),
            "state": state,
            "redirect_uri": callback_uri,
            "status": "pending",
            "message": "",
            "code": "",
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            "auth_url": "",
        }
        self.OAUTH_SESSIONS[state] = session
        run_payload = dict(payload)
        run_payload["redirect_uri"] = callback_uri
        run_payload["state"] = state
        env = self._provider_env(provider, run_payload)
        if target == "calendar" and provider == "google":
            tool = self._agent_tool_path("google_calendar_oauth.py")
            proc = subprocess.run(
                ["python3", tool, "auth-url"],
                text=True,
                capture_output=True,
                env=env,
                timeout=20,
            )
        elif target == "calendar" and provider == "microsoft":
            tool = self._agent_tool_path("microsoft_outlook_oauth.py")
            env["AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE"] = (
                "offline_access https://graph.microsoft.com/Calendars.ReadWrite"
            )
            proc = subprocess.run(
                ["python3", tool, "auth-url"],
                text=True,
                capture_output=True,
                env=env,
                timeout=20,
            )
        elif target == "email" and provider == "gmail":
            tool = self._agent_tool_path("google_gmail_oauth.py")
            proc = subprocess.run(
                ["python3", tool, "auth-url"],
                text=True,
                capture_output=True,
                env=env,
                timeout=20,
            )
        elif target == "email" and provider == "outlook":
            tool = self._agent_tool_path("microsoft_outlook_oauth.py")
            env["AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE"] = (
                "offline_access https://graph.microsoft.com/Mail.ReadWrite"
            )
            proc = subprocess.run(
                ["python3", tool, "auth-url"],
                text=True,
                capture_output=True,
                env=env,
                timeout=20,
            )
        else:
            return True, {"status": "ok", "message": "No OAuth needed for this provider."}

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            session["status"] = "error"
            session["message"] = err or out or "OAuth start failed."
            session["updated_at"] = int(time.time())
            return False, {"status": "error", "message": err or out or "OAuth start failed."}
        url = self._extract_url(out)
        session["auth_url"] = url
        session["message"] = "Open the authorization page and approve access."
        session["updated_at"] = int(time.time())
        return True, {
            "status": "ok",
            "state": state,
            "auth_url": url,
            "message": "Authorization URL ready. Approve access and we’ll finish setup automatically.",
            "raw": out,
        }

    def _oauth_finish(self, target, provider, payload):
        code = str(payload.get("code", "")).strip()
        if not code:
            return False, {"status": "error", "message": "Authorization code is required."}
        env = self._provider_env(provider, payload)
        if target == "calendar" and provider == "google":
            tool = self._agent_tool_path("google_calendar_oauth.py")
            proc = subprocess.run(
                ["python3", tool, "exchange", code],
                text=True,
                capture_output=True,
                env=env,
                timeout=25,
            )
        elif target == "calendar" and provider == "microsoft":
            tool = self._agent_tool_path("microsoft_outlook_oauth.py")
            env["AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE"] = (
                "offline_access https://graph.microsoft.com/Calendars.ReadWrite"
            )
            proc = subprocess.run(
                ["python3", tool, "exchange", code],
                text=True,
                capture_output=True,
                env=env,
                timeout=25,
            )
        elif target == "email" and provider == "gmail":
            tool = self._agent_tool_path("google_gmail_oauth.py")
            proc = subprocess.run(
                ["python3", tool, "exchange", code],
                text=True,
                capture_output=True,
                env=env,
                timeout=25,
            )
        elif target == "email" and provider == "outlook":
            tool = self._agent_tool_path("microsoft_outlook_oauth.py")
            env["AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE"] = (
                "offline_access https://graph.microsoft.com/Mail.ReadWrite"
            )
            proc = subprocess.run(
                ["python3", tool, "exchange", code],
                text=True,
                capture_output=True,
                env=env,
                timeout=25,
            )
        else:
            return True, {"status": "ok", "message": "No OAuth needed for this provider."}

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            return False, {"status": "error", "message": err or out or "OAuth exchange failed."}
        return True, {"status": "ok", "message": out or "Provider connected."}

    def _oauth_session_for(self, target):
        target = str(target or "").strip().lower()
        if target not in ("calendar", "email"):
            return None
        latest = None
        for sess in self.OAUTH_SESSIONS.values():
            if sess.get("target") != target:
                continue
            if latest is None or int(sess.get("updated_at", 0)) > int(latest.get("updated_at", 0)):
                latest = sess
        return latest

    def _oauth_handle_callback(self, parsed):
        qs = parse_qs(parsed.query or "")
        state = (qs.get("state") or [""])[0].strip()
        code = (qs.get("code") or [""])[0].strip()
        error = (qs.get("error") or [""])[0].strip()
        sess = self.OAUTH_SESSIONS.get(state) if state else None

        if not sess:
            return False, "Connection session was not found or expired."
        if error:
            sess["status"] = "error"
            sess["message"] = f"Authorization failed: {error}"
            sess["updated_at"] = int(time.time())
            return False, sess["message"]
        if not code:
            sess["status"] = "error"
            sess["message"] = "Authorization did not return a valid code."
            sess["updated_at"] = int(time.time())
            return False, sess["message"]

        sess["code"] = code
        finish_payload = {
            "target": sess.get("target"),
            "provider": sess.get("provider"),
            "client_id": sess.get("client_id", ""),
            "client_secret": sess.get("client_secret", ""),
            "redirect_uri": sess.get("redirect_uri", ""),
            "code": code,
        }
        ok, body = self._oauth_finish(sess.get("target"), sess.get("provider"), finish_payload)
        sess["status"] = "connected" if ok else "error"
        sess["message"] = str(body.get("message", "Connected." if ok else "Connection failed."))
        sess["updated_at"] = int(time.time())
        return ok, sess["message"]

    def _provider_test(self, target, provider):
        env = os.environ.copy()
        if target == "calendar":
            env["AI_DISTRO_CALENDAR_PROVIDER"] = provider
            tool = self._agent_tool_path("calendar_router.py")
            proc = subprocess.run(
                ["python3", tool, "list", "today"],
                text=True,
                capture_output=True,
                env=env,
                timeout=15,
            )
        elif target == "email":
            env["AI_DISTRO_EMAIL_PROVIDER"] = provider
            tool = self._agent_tool_path("email_router.py")
            proc = subprocess.run(
                ["python3", tool, "summary", "in:inbox newer_than:2d"],
                text=True,
                capture_output=True,
                env=env,
                timeout=15,
            )
        else:
            return False, "unknown test target"
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout or "Provider test failed.").strip()
        return True, (proc.stdout or "Provider test passed.").strip()

    def translate_path(self, path):
        static_root = os.environ.get("AI_DISTRO_SHELL_STATIC_DIR", DEFAULT_STATIC)
        rel = path.lstrip("/")
        if not rel:
            rel = "index.html"
        return os.path.join(static_root, rel)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/oauth/callback":
            ok, message = self._oauth_handle_callback(parsed)
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            title = "Connected" if ok else "Connection Failed"
            body = (
                f"<h2>{title}</h2><p>{message}</p><p>You can close this tab and return to AI Distro Shell.</p>"
            )
            self.wfile.write(
                f"<!doctype html><html><body style='font-family:sans-serif;padding:24px'>{body}</body></html>".encode(
                    "utf-8"
                )
            )
            return
        if self.path.startswith("/api/"):
            if self.path == "/api/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "persona": self._load_persona()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/persona":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "persona": self._load_persona()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/persona-presets":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "presets": self._load_persona_presets()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/onboarding":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "state": self._load_onboarding()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/providers":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "providers": self._load_providers()}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if self.path == "/api/app-tasks":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {"status": "ok", "tasks": self._load_recent_task_events(limit=8)}
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            if parsed.path == "/api/provider/connect/status":
                target = (parse_qs(parsed.query or "").get("target") or [""])[0].strip().lower()
                sess = self._oauth_session_for(target)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if not sess:
                    self.wfile.write(json.dumps({"status": "idle", "target": target}).encode("utf-8"))
                    return
                payload = {
                    "status": str(sess.get("status", "pending")),
                    "target": str(sess.get("target", "")),
                    "provider": str(sess.get("provider", "")),
                    "message": str(sess.get("message", "")),
                    "auth_url": str(sess.get("auth_url", "")),
                    "updated_at": int(sess.get("updated_at", 0)),
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return
            self.send_error(404, "unknown api")
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/provider/connect/start":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            target = str(payload.get("target", "")).strip().lower()
            provider = str(payload.get("provider", "")).strip().lower()
            if target not in ("calendar", "email"):
                self.send_error(400, "invalid target")
                return
            ok, body = self._oauth_start(target, provider, payload)
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode("utf-8"))
            return
        if parsed.path == "/api/provider/connect/finish":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            target = str(payload.get("target", "")).strip().lower()
            provider = str(payload.get("provider", "")).strip().lower()
            if target not in ("calendar", "email"):
                self.send_error(400, "invalid target")
                return
            ok, body = self._oauth_finish(target, provider, payload)
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode("utf-8"))
            return
        if parsed.path == "/api/provider/test":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            target = str(payload.get("target", "")).strip().lower()
            provider = str(payload.get("provider", "")).strip().lower()
            if target not in ("calendar", "email"):
                self.send_error(400, "invalid target")
                return
            ok, message = self._provider_test(target, provider)
            code = 200 if ok else 500
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok" if ok else "error", "message": message}).encode("utf-8"))
            return
        if parsed.path == "/api/persona/set":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            preset = (payload.get("preset") or "").strip().lower()
            ok, detail = self._write_persona(preset)
            if not ok:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                msg = {"status": "error", "message": f"could not persist persona: {detail}"}
                self.wfile.write(json.dumps(msg).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            msg = {"status": "ok", "path": detail}
            self.wfile.write(json.dumps(msg).encode("utf-8"))
            return
        if parsed.path == "/api/onboarding":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            state = payload.get("state")
            if not isinstance(state, dict):
                self.send_error(400, "state must be object")
                return
            ok, detail = self._write_onboarding(state)
            if not ok:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                msg = {"status": "error", "message": f"could not persist onboarding: {detail}"}
                self.wfile.write(json.dumps(msg).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            msg = {"status": "ok", "path": detail}
            self.wfile.write(json.dumps(msg).encode("utf-8"))
            return
        if parsed.path == "/api/providers":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid json")
                return
            providers = payload.get("providers")
            if not isinstance(providers, dict):
                self.send_error(400, "providers must be object")
                return
            ok, detail = self._write_providers(providers)
            if not ok:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                msg = {"status": "error", "message": f"could not persist providers: {detail}"}
                self.wfile.write(json.dumps(msg).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            msg = {"status": "ok", "path": detail, "providers": self._load_providers()}
            self.wfile.write(json.dumps(msg).encode("utf-8"))
            return
        if parsed.path != "/api/command":
            self.send_error(404, "unknown api")
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "invalid json")
            return
        name = (payload.get("name") or "").strip()
        if name:
            request = {
                "version": 1,
                "name": name,
                "payload": payload.get("payload"),
            }
        else:
            text = (payload.get("text") or "").strip()
            if not text:
                self.send_error(400, "missing text")
                return
            request = {"version": 1, "name": "natural_language", "payload": text}
        try:
            response = agent_request(request)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            msg = {"status": "error", "message": f"agent unavailable: {exc}"}
            self.wfile.write(json.dumps(msg).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))


def run():
    host = os.environ.get("AI_DISTRO_SHELL_HOST", "127.0.0.1")
    port = int(os.environ.get("AI_DISTRO_SHELL_PORT", "17842"))
    server = HTTPServer((host, port), ShellHandler)
    print(f"ai-distro-shell listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
