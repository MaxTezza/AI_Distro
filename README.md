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
- Provider choices are persisted at `~/.config/ai-distro/providers.json` and can be changed from shell settings.
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

## Tuning Utility Safely
Policy controls live in `configs/policy.json`:
- `open_url_allowed_domains`
- `open_app_allowed`
- `list_files_allowed_prefixes`
- `rate_limit_per_minute_default`
- `rate_limit_per_minute_overrides`

Increase utility by extending these allowlists, instead of allowing arbitrary command execution.

Agent outcomes are also written to a JSONL audit trail (`AI_DISTRO_AUDIT_LOG`) for incident review and tuning.
Audit entries are hash-chained and survive rotation (`AI_DISTRO_AUDIT_ROTATE_BYTES`) with continuity anchors.

## Plugin Providers
Core actions stay stable while providers are swappable:
- Calendar: `local`, `google` (microsoft planned)
- Email: `gmail` (outlook planned)

Set providers in shell settings or via env:
- `AI_DISTRO_CALENDAR_PROVIDER`
- `AI_DISTRO_EMAIL_PROVIDER`
- `AI_DISTRO_WEATHER_PROVIDER`

## Weather + Calendar Outfit Recommendation (v1)
Say:
- `what should i wear today`
- `what should i wear tomorrow`
- `weather today`
- `what is on my calendar today`
- `add calendar event tomorrow at 3pm dentist appointment`
- `summarize my email`
- `search my email for invoice`
- `draft email to alex@example.com about project update`

This uses weather forecast + local calendar events from:
- `AI_DISTRO_CALENDAR_EVENTS_FILE` (default: `~/.config/ai-distro/calendar-events.json`)

Google Calendar (optional, preferred):
- Set `AI_DISTRO_GOOGLE_CLIENT_ID` and `AI_DISTRO_GOOGLE_CLIENT_SECRET`
- Generate refresh token:
  - `python3 tools/agent/google_calendar_oauth.py auth-url`
  - Authorize in browser, copy `code` from redirect URL
  - `python3 tools/agent/google_calendar_oauth.py exchange "<code>"`
- This writes `~/.config/ai-distro/google-calendar-oauth.json`
- `plan_day_outfit` will use Google Calendar events first, then fall back to local JSON.

Gmail (optional, read-only):
- Set `AI_DISTRO_GOOGLE_CLIENT_ID` and `AI_DISTRO_GOOGLE_CLIENT_SECRET`
- Generate refresh token:
  - `python3 tools/agent/google_gmail_oauth.py auth-url`
  - Authorize in browser, copy `code` from redirect URL
  - `python3 tools/agent/google_gmail_oauth.py exchange "<code>"`
- This writes `~/.config/ai-distro/google-gmail-oauth.json`
- Then use `summarize my email`, `search my email for <query>`, and `draft email to <address> about <subject>`.

Example file:

```json
[
  {
    "date": "2026-02-16",
    "start": "09:00",
    "title": "Office planning meeting",
    "dress_code": "business",
    "outdoor": false
  },
  {
    "date": "2026-02-16",
    "start": "18:00",
    "title": "Evening walk",
    "dress_code": "casual",
    "outdoor": true
  }
]
```

## Docs
- `docs/VOICE_UX.md`
- `docs/DESKTOP_UI.md`
- `docs/IPC.md`
- `docs/RUNTIME_ENV.md`
- `docs/VOICE_ACCEPTANCE.md`
- `docs/TOP20_TASKS.md`
- `docs/PROJECT_BRIEF.md`
