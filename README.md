# AI Distro

Voice-first, agentic Linux distro workbench focused on useful day-to-day automation with strict safety controls.

## Current Status
- Bootable ISO pipeline exists.
- Voice Top 20 command gate is automated and passing.
- Shell UI includes **Onboarding Wizard v1** with resume/replay support.

## Quickstart

Run the quality gate:

```bash
cd /home/jmt3/AI_Distro
make qa-voice
```

Run the shell UI locally:

```bash
cd /home/jmt3/AI_Distro
AI_DISTRO_SHELL_STATIC_DIR="$PWD/assets/ui/shell" \
python3 tools/shell/ai_distro_shell.py
```

Then open `http://127.0.0.1:17842/` in a browser.

Notes:
- On first run, the onboarding wizard walks through voice replies, persona, safety, and a first command.
- Onboarding progress is persisted at `~/.config/ai-distro/shell-onboarding.json`.
- If `ai-distro-agent` is not running, shell status will show offline/agent unavailable.

## Product Guardrails
- No destructive action should execute without confirmation.
- Confirmation behavior is a release gate, not optional UX.
- Reliability on common tasks is prioritized over adding low-value commands.

## Security Direction (Agent Layer)
- Keep action scope explicit via intent mapping and policy checks.
- Deny by default for unknown or high-risk actions.
- Require confirmation for package, power, and other risky operations.
- Keep memory writes explicit (`remember ...`) and user-controlled.

## Docs
- `docs/VOICE_UX.md`
- `docs/DESKTOP_UI.md`
- `docs/IPC.md`
- `docs/RUNTIME_ENV.md`
- `docs/VOICE_ACCEPTANCE.md`
- `docs/TOP20_TASKS.md`
- `docs/PROJECT_BRIEF.md`
