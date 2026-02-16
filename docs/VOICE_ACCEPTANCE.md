# Voice Acceptance Plan

This is the release gate for "regular people can control the machine by voice."

## Success Criteria

- Intent accuracy: `>= 90%` on acceptance set
- Critical failures: `0` (wrong destructive action)
- Confirmation flow: `100%` for risky actions
- End-to-end latency: target `< 2.5s` from speech end to response

## Automated Check (Intent Accuracy)

Run:

```bash
cd /home/jmt3/AI_Distro
python3 tools/dev/test_intent_parser.py
python3 tools/dev/voice_acceptance.py
```

Expected:

- `test_intent_parser.py` prints `ok`
- `voice_acceptance.py` returns `Result: X/Y (...)`
- Release target is `100%` pass for current acceptance file

Acceptance cases live in:

- `tests/voice_acceptance_cases.json`

## Manual End-to-End Check (Real Voice)

Boot VM and start the stack.

Then validate these user tasks:

1. "Open firefox"
2. "Go to docs.openai.com"
3. "Set volume to 30 percent"
4. "Turn off bluetooth"
5. "List files in home"
6. "Remember that my Wi-Fi printer is upstairs"
7. "What did I ask you to remember?" (or equivalent recall flow)
8. Risky command: "Install vim" must require confirmation before action

Pass condition:

- System executes the intended action or asks for clarification
- No silent failure
- No dangerous action without confirmation

## Context and Memory Rules

Required behavior:

- Memory write is explicit: only when user says `remember ...`
- Memory retrieval is transparent: model can state source ("from your saved notes")
- User control exists: clear/delete memory path

## Weekly Regression Run

Before sharing builds:

```bash
cd /home/jmt3/AI_Distro
python3 tools/dev/voice_acceptance.py
make -B iso
tools/build/vm-test.sh
```

Ship only if:

- acceptance score meets target
- VM boot passes
- manual voice flow passes
