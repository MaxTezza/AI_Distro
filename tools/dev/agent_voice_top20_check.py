#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARSER = ROOT / "tools" / "agent" / "intent_parser.py"
CASES = ROOT / "tests" / "agent_voice_top20_cases.json"


def run_parser(text: str) -> dict:
    out = subprocess.check_output([sys.executable, str(PARSER), text], text=True)
    return json.loads(out)


def expand_expected_payload(payload):
    if payload is None:
        return None
    return payload.replace("__HOME__", os.environ.get("HOME", "/home/casper"))


def main() -> int:
    with open(CASES, "r", encoding="utf-8") as f:
        cases = json.load(f)

    passed = 0
    total = len(cases)
    print(f"Running agent Top 20 checks: {total}")

    for idx, case in enumerate(cases, start=1):
        utterance = case["utterance"]
        expected_name = case["name"]
        expected_payload = expand_expected_payload(case.get("payload"))
        try:
            got = run_parser(utterance)
        except Exception as err:
            print(f"[{idx:02d}] FAIL parser error: {utterance!r} ({err})")
            continue

        got_name = got.get("name")
        got_payload = got.get("payload")
        got_version = got.get("version")
        ok = (
            got_version == 1
            and got_name == expected_name
            and got_payload == expected_payload
        )
        if ok:
            passed += 1
            print(f"[{idx:02d}] PASS {utterance!r} -> {got_name} {got_payload!r}")
        else:
            print(
                f"[{idx:02d}] FAIL {utterance!r} -> "
                f"got(version={got_version}, name={got_name}, payload={got_payload!r}) "
                f"expected(version=1, name={expected_name}, payload={expected_payload!r})"
            )

    score = (passed / total) * 100 if total else 0
    print(f"Result: {passed}/{total} ({score:.1f}%)")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
