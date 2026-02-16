# Runtime Environment Variables

## Agent
- `AI_DISTRO_IPC_SOCKET` (default: `/run/ai-distro/agent.sock`)
  Path to Unix socket for IPC.

- `AI_DISTRO_IPC_STDIN` (default: unset)
  If set to `1`, run the IPC loop over stdin/stdout.

- `AI_DISTRO_INTENT_PARSER` (default: `/usr/lib/ai-distro/intent_parser.py`)
  Path to the intent parser CLI for natural language requests.

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
