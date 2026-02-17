#!/usr/bin/env python3
import argparse
import json
import tempfile
from pathlib import Path


def fnv1a64_hex(input_bytes: bytes) -> str:
    h = 0xCBF29CE484222325
    for b in input_bytes:
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


def compute_chain_hash(seq: int, prev_hash: str, event_json: str) -> str:
    chain_input = f"{seq}|{prev_hash}|{event_json}"
    return fnv1a64_hex(chain_input.encode("utf-8"))


def _canonical_event_json(event_obj: dict) -> str:
    # Match serde_json::to_string compact output.
    return json.dumps(event_obj, separators=(",", ":"), ensure_ascii=False)


def verify_log(log_path: Path) -> tuple[bool, str, int, str]:
    if not log_path.exists():
        return False, f"log file not found: {log_path}", 0, "genesis"

    last_seq = 0
    last_hash = "genesis"
    line_count = 0

    with log_path.open("r", encoding="utf-8") as fh:
        for idx, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            line_count += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                return False, f"{log_path}:{idx}: invalid json ({exc})", last_seq, last_hash

            if not isinstance(obj, dict):
                return False, f"{log_path}:{idx}: event is not object", last_seq, last_hash

            if "seq" not in obj or "prev_hash" not in obj or "chain_hash" not in obj:
                return False, f"{log_path}:{idx}: missing seq/prev_hash/chain_hash", last_seq, last_hash

            seq = obj.get("seq")
            prev_hash = obj.get("prev_hash")
            chain_hash = obj.get("chain_hash")
            if not isinstance(seq, int) or seq <= 0:
                return False, f"{log_path}:{idx}: invalid seq", last_seq, last_hash
            if not isinstance(prev_hash, str) or not isinstance(chain_hash, str):
                return False, f"{log_path}:{idx}: invalid hash fields", last_seq, last_hash

            if idx > 1 and seq != last_seq + 1:
                return False, f"{log_path}:{idx}: non-consecutive seq (got {seq}, expected {last_seq + 1})", last_seq, last_hash
            if idx > 1 and prev_hash != last_hash:
                return False, f"{log_path}:{idx}: prev_hash mismatch", last_seq, last_hash

            event_without_chain = dict(obj)
            event_without_chain.pop("chain_hash", None)
            event_json = _canonical_event_json(event_without_chain)
            expected = compute_chain_hash(seq, prev_hash, event_json)
            if expected != chain_hash:
                return False, f"{log_path}:{idx}: chain hash mismatch", last_seq, last_hash

            last_seq = seq
            last_hash = chain_hash

    return True, "ok", last_seq, last_hash


def verify_state(state_path: Path, expected_seq: int, expected_hash: str) -> tuple[bool, str]:
    if not state_path.exists():
        return False, f"state file not found: {state_path}"
    try:
        obj = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"invalid state json ({exc})"
    if not isinstance(obj, dict):
        return False, "state is not an object"
    seq = obj.get("seq")
    last_hash = obj.get("last_hash")
    if seq != expected_seq or last_hash != expected_hash:
        return False, f"state mismatch (seq={seq}, hash={last_hash}) expected ({expected_seq}, {expected_hash})"
    return True, "ok"


def append_event(path: Path, state: dict, event_obj: dict):
    seq = state["seq"] + 1
    prev = state["last_hash"]
    obj = dict(event_obj)
    obj["seq"] = seq
    obj["prev_hash"] = prev
    event_json = _canonical_event_json(obj)
    obj["chain_hash"] = compute_chain_hash(seq, prev, event_json)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
        fh.write("\n")
    state["seq"] = seq
    state["last_hash"] = obj["chain_hash"]


def run_self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="ai-distro-audit-chain-") as td:
        root = Path(td)
        log = root / "audit.jsonl"
        state_file = root / "audit.jsonl.state"
        state = {"seq": 0, "last_hash": "genesis"}

        append_event(
            log,
            state,
            {
                "ts": 1700000000,
                "type": "action_outcome",
                "action": "ping",
                "status": "ok",
                "message": "pong",
                "request_version": 1,
                "has_confirmation_id": False,
                "payload_len": 0,
                "payload_hash": None,
            },
        )
        append_event(
            log,
            state,
            {
                "ts": 1700000001,
                "type": "rotation_anchor",
                "rotated_file": "/tmp/audit.1700000001.jsonl",
            },
        )
        append_event(
            log,
            state,
            {
                "ts": 1700000002,
                "type": "action_outcome",
                "action": "calendar_list_day",
                "status": "ok",
                "message": "Events for 2026-02-17",
                "request_version": 1,
                "has_confirmation_id": False,
                "payload_len": 5,
                "payload_hash": 1234,
            },
        )
        state_file.write_text(json.dumps(state, separators=(",", ":")), encoding="utf-8")

        ok, msg, last_seq, last_hash = verify_log(log)
        if not ok:
            print(f"self-test failed: {msg}")
            return 1
        ok_state, state_msg = verify_state(state_file, last_seq, last_hash)
        if not ok_state:
            print(f"self-test failed: {state_msg}")
            return 1

        tampered = log.read_text(encoding="utf-8").replace("calendar_list_day", "calendar_add_event", 1)
        log.write_text(tampered, encoding="utf-8")
        ok2, _, _, _ = verify_log(log)
        if ok2:
            print("self-test failed: tamper detection did not fail")
            return 1

    print("ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify AI Distro audit hash chain integrity.")
    parser.add_argument("--log", type=Path, help="Path to audit log JSONL file.")
    parser.add_argument("--state", type=Path, help="Path to audit state JSON file.")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic self-test fixture.")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if not args.log:
        parser.error("--log is required unless --self-test is used")

    state_path = args.state if args.state else Path(f"{args.log}.state")
    ok, msg, last_seq, last_hash = verify_log(args.log)
    if not ok:
        print(msg)
        return 1
    ok_state, state_msg = verify_state(state_path, last_seq, last_hash)
    if not ok_state:
        print(state_msg)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
