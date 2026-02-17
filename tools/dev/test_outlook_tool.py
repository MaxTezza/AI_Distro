#!/usr/bin/env python3
import importlib.util
from pathlib import Path


def load_module():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "tools" / "agent" / "outlook_tool.py"
    spec = importlib.util.spec_from_file_location("outlook_tool", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_parse_draft_payload():
    mod = load_module()
    parsed = mod.parse_draft_payload("alex@example.com|Hello|Body line")
    assert parsed is not None
    assert parsed["to"] == "alex@example.com"
    assert parsed["subject"] == "Hello"


def test_cmd_draft_posts_to_graph():
    mod = load_module()
    seen = {}

    def fake_post(token, url, payload):
        seen["token"] = token
        seen["url"] = url
        seen["payload"] = payload
        return {"id": "draft-123"}

    mod.graph_post = fake_post
    out = mod.cmd_draft("tok", "alex@example.com|Project update|Hi Alex")
    assert out == "Draft created for alex@example.com with subject 'Project update'."
    assert seen["token"] == "tok"
    assert seen["url"] == "https://graph.microsoft.com/v1.0/me/messages"
    assert seen["payload"]["subject"] == "Project update"
    assert seen["payload"]["toRecipients"][0]["emailAddress"]["address"] == "alex@example.com"
    assert seen["payload"]["body"]["content"] == "Hi Alex"


def main():
    test_parse_draft_payload()
    test_cmd_draft_posts_to_graph()
    print("ok")


if __name__ == "__main__":
    main()
