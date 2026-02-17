#!/usr/bin/env python3
import json
import os
import socket
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

DEFAULT_SOCKET = "/run/ai-distro/agent.sock"
DEFAULT_STATIC = "/usr/share/ai-distro/ui/shell"
DEFAULT_PERSONA = "/etc/ai-distro/persona.json"
DEFAULT_PERSONA_ALFRED = "/etc/ai-distro/persona.alfred.json"
DEFAULT_ONBOARDING = os.path.expanduser("~/.config/ai-distro/shell-onboarding.json")
DEFAULT_PROVIDERS = os.path.expanduser("~/.config/ai-distro/providers.json")


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

    def translate_path(self, path):
        static_root = os.environ.get("AI_DISTRO_SHELL_STATIC_DIR", DEFAULT_STATIC)
        rel = path.lstrip("/")
        if not rel:
            rel = "index.html"
        return os.path.join(static_root, rel)

    def do_GET(self):
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
            self.send_error(404, "unknown api")
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
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
