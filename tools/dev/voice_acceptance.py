#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARSER = ROOT / "tools" / "dev" / "intent_parser.py"
CASES = ROOT / "tests" / "voice_acceptance_cases.json"


def run_parser(text: str) -> dict:
    out = subprocess.check_output([sys.executable, str(PARSER), text], text=True)
    return json.loads(out)


def main() -> int:
    with open(CASES, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total = len(cases)
    passed = 0

    print(f"Running voice acceptance cases: {total}")
    for idx, case in enumerate(cases, start=1):
        utterance = case["utterance"]
        expected_intent = case["intent"]
        expected_payload = case.get("payload")

        try:
            got = run_parser(utterance)
        except Exception as err:
            print(f"[{idx:02d}] FAIL parser error: {utterance!r} ({err})")
            continue

        got_intent = got.get("intent")
        got_payload = got.get("payload")
        ok = got_intent == expected_intent and got_payload == expected_payload
        if ok:
            passed += 1
            print(f"[{idx:02d}] PASS {utterance!r} -> {got_intent} {got_payload!r}")
        else:
            print(
                f"[{idx:02d}] FAIL {utterance!r} -> got({got_intent}, {got_payload!r}) "
                f"expected({expected_intent}, {expected_payload!r})"
            )

    score = (passed / total) * 100 if total else 0
    print(f"Result: {passed}/{total} ({score:.1f}%)")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
