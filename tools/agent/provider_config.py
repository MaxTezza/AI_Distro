#!/usr/bin/env python3
import json
import os


DEFAULT_PROVIDERS = {
    "calendar": "local",
    "email": "gmail",
    "weather": "default",
}


def providers_path() -> str:
    return os.environ.get(
        "AI_DISTRO_PROVIDERS_FILE",
        os.path.expanduser("~/.config/ai-distro/providers.json"),
    )


def load_providers() -> dict:
    cfg = dict(DEFAULT_PROVIDERS)
    path = providers_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(k, str) and isinstance(v, str):
                    cfg[k] = v.strip().lower()
    except Exception:
        pass

    for env_key, key in (
        ("AI_DISTRO_CALENDAR_PROVIDER", "calendar"),
        ("AI_DISTRO_EMAIL_PROVIDER", "email"),
        ("AI_DISTRO_WEATHER_PROVIDER", "weather"),
    ):
        val = os.environ.get(env_key, "").strip().lower()
        if val:
            cfg[key] = val
    return cfg

