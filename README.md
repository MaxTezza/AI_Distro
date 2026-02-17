# AI Distro

Voice-first, agentic Linux distro workbench focused on useful day-to-day automation with strict safety controls.

## Current Status
- Bootable ISO pipeline exists.
- **Local LLM Brain:** Llama 3.2 1B running locally for natural language understanding (Zero API keys).
- **Nervous System (Event Bus):** Deep D-Bus integration for proactive alerts (Low battery, Network changes).
- **Conversational UI:** Modern shell with "thinking" states and proactive messaging.
- **Asynchronous IPC (Tokio):** Core agent refactored for non-blocking concurrent requests.
- **Secure Audit Logging:** SHA-256 hash chains for tamper-evident record keeping.
- **Modularized Core:** Decoupled handlers (package, system, media, etc.) for better maintainability.
- **Automated Quality Gate:** GitHub Actions CI for build, test, and linting.
- **Containerized Deployment:** Docker support for easy environment isolation.

### Docker (Headless Agent)
You can run the AI Distro agent in a container for testing or headless server usage.

**Build:**
```bash
docker build -t ai-distro-agent .
```

**Run:**
```bash
docker run -v /tmp:/tmp -e AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock ai-distro-agent
```

## Natural Language Guide

Speak naturally to your assistant. You don't need to memorize commands.

**Try saying:**
- "I want to browse the web" (opens Firefox)
- "Play some music" (opens Spotify)
- "I need to write code" (opens VS Code)
- "It's too loud" (mutes volume)
- "Dark mode please" (lowers brightness)
- "Get me ready for the day" (checks weather, calendar, email)
- "Lock my computer" (sleep mode)

**Proactive Features:**
The assistant will reach out when it notices things like your battery getting low or a change in your network connection.

## Architecture

AI Distro follows a hybrid model:
- **Rust Agent (Core):** Handles async IPC, system events (Nervous System), and security policy.
- **Python Intelligence (Brain):** Local LLM-based intent parsing and complex reasoning.
- **Web Shell (Face):** Responsive dashboard for interacting with the assistant.


## Quickstart

### Local Development (Rust Agent)
```bash
cd src/rust/ai-distro-agent
cargo build --release
AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock ./target/release/ai-distro-agent
```

### Docker
```bash
docker build -t ai-distro-agent .
docker run -e AI_DISTRO_IPC_SOCKET=/tmp/ai-distro.sock ai-distro-agent
```

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
- Calendar: `local`, `google`, `microsoft`
- Email: `gmail`, `outlook`, `imap`

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
- `install discord`
- `uninstall vlc`
- `update my apps`

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

Outlook (optional):
- Set `AI_DISTRO_MICROSOFT_CLIENT_ID` and `AI_DISTRO_MICROSOFT_CLIENT_SECRET`
- Generate refresh token:
  - `python3 tools/agent/microsoft_outlook_oauth.py auth-url`
  - Authorize in browser, copy `code` from redirect URL
  - `python3 tools/agent/microsoft_outlook_oauth.py exchange "<code>"`
- This writes `~/.config/ai-distro/microsoft-outlook-oauth.json`
- Set email provider to `outlook` in shell settings.
- For draft support, include `Mail.ReadWrite` when generating tokens:
  - `AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE="offline_access https://graph.microsoft.com/Mail.ReadWrite" python3 tools/agent/microsoft_outlook_oauth.py auth-url`

Microsoft Calendar (optional):
- Set `AI_DISTRO_MICROSOFT_CLIENT_ID` and `AI_DISTRO_MICROSOFT_CLIENT_SECRET`
- Generate refresh token:
  - `AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE="offline_access https://graph.microsoft.com/Calendars.ReadWrite" python3 tools/agent/microsoft_outlook_oauth.py auth-url`
  - Authorize in browser, copy `code` from redirect URL
  - `AI_DISTRO_MICROSOFT_OUTLOOK_SCOPE="offline_access https://graph.microsoft.com/Calendars.ReadWrite" python3 tools/agent/microsoft_outlook_oauth.py exchange "<code>"`
- This writes `~/.config/ai-distro/microsoft-outlook-oauth.json`
- Set calendar provider to `microsoft` in shell settings.

IMAP / Proton Bridge (optional, read-only):
- Set email provider to `imap` in shell settings.
- Configure:
  - `AI_DISTRO_IMAP_HOST`
  - `AI_DISTRO_IMAP_PORT` (usually `993`)
  - `AI_DISTRO_IMAP_USERNAME`
  - `AI_DISTRO_IMAP_PASSWORD`
  - optional `AI_DISTRO_IMAP_FOLDER` (default `INBOX`)
- For Proton Mail, point host/port/user/password to Proton Bridge local credentials.

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
