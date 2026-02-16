# Configuration

## Persona
- `configs/persona.json` defines the assistant personality and filler phrases.
- `configs/persona.alfred.json` provides an Alfred-style preset.
- The shell server exposes persona data via `/api/health` and `/api/persona`.
- The shell UI allows toggling between Max and Alfred presets locally.
- Override the file path with `AI_DISTRO_PERSONA`.
 - The shell UI also attempts to persist the selection system-wide via `/api/persona/set`.
