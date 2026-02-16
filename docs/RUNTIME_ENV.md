# Runtime Environment Variables

## Agent
- `AI_DISTRO_IPC_SOCKET` (default: `/run/ai-distro/agent.sock`)
  Path to Unix socket for IPC.

- `AI_DISTRO_IPC_SOCKET_MODE` (default: `660`)
  Octal permission mode applied to the IPC socket (for example: `660`, `600`).

- `AI_DISTRO_IPC_STDIN` (default: unset)
  If set to `1`, run the IPC loop over stdin/stdout.

- `AI_DISTRO_INTENT_PARSER` (default: `/usr/lib/ai-distro/intent_parser.py`)
  Path to the intent parser CLI for natural language requests.

- `AI_DISTRO_DAY_PLANNER` (default: `/usr/lib/ai-distro/day_planner.py`)
  Helper script for weather + calendar clothing recommendations (`plan_day_outfit`).

- `AI_DISTRO_WEATHER_TOOL` (default: `/usr/lib/ai-distro/weather_tool.py`)
  Helper script for direct forecast requests (`weather_get`).

- `AI_DISTRO_CALENDAR_TOOL` (default: `/usr/lib/ai-distro/calendar_tool.py`)
  Helper script for local calendar add/list requests (`calendar_add_event`, `calendar_list_day`).

- `AI_DISTRO_GOOGLE_CALENDAR_OAUTH_FILE` (default: `~/.config/ai-distro/google-calendar-oauth.json`)
  OAuth config for Google Calendar integration (`client_id`, `client_secret`, `refresh_token`, `calendar_id`).

- `AI_DISTRO_GOOGLE_CLIENT_ID`, `AI_DISTRO_GOOGLE_CLIENT_SECRET`, `AI_DISTRO_GOOGLE_REFRESH_TOKEN`
  Optional env overrides for Google Calendar OAuth credentials.

- `AI_DISTRO_GOOGLE_CALENDAR_ID` (default: `primary`)
  Calendar ID used for Google Calendar event fetch.

- `AI_DISTRO_INTENT_STDIN` (default: unset)
  If set to `1`, read natural language text from stdin and emit intent JSON.

## Confirmations
- `AI_DISTRO_CONFIRM_DIR` (default: `/var/lib/ai-distro-agent/confirmations`)
  Directory to persist pending confirmation records.

- `AI_DISTRO_CONFIRM_TTL_SECS` (default: `300`)
  Confirmation expiration time in seconds.

- `AI_DISTRO_CONFIRM_CLEANUP_SECS` (default: `300`)
  Cleanup interval in seconds.

## Shell
- `AI_DISTRO_SHELL_HOST` (default: `127.0.0.1`)
  Shell server bind address.

- `AI_DISTRO_SHELL_PORT` (default: `17842`)
  Shell server port.

- `AI_DISTRO_SHELL_STATIC_DIR` (default: `/usr/share/ai-distro/ui/shell`)
  Path to shell UI assets.

- `AI_DISTRO_PERSONA` (default: `/etc/ai-distro/persona.json`)
  Path to assistant persona configuration.

- `AI_DISTRO_AUDIT_LOG` (default: `/var/log/ai-distro-agent/audit.jsonl`)
  JSONL audit trail destination for action outcomes (request metadata, decision/result status).

- `AI_DISTRO_AUDIT_STATE` (default: `${AI_DISTRO_AUDIT_LOG}.state`)
  Path for persisted hash-chain state (`seq`, `last_hash`) used to verify continuity across restarts.

- `AI_DISTRO_AUDIT_ROTATE_BYTES` (default: `5242880`)
  Rotate audit log when it reaches this size (bytes); a hash-chained rotation anchor is written into the new file.

- `AI_DISTRO_WEATHER_LOCATION` (default: `Austin`)
  Location passed to the day planner weather fetch.

- `AI_DISTRO_CALENDAR_EVENTS_FILE` (default: `~/.config/ai-distro/calendar-events.json`)
  Local calendar events source used by the day planner.
