# Voice UX (v1)

## Goal
Enable natural English control for system tasks on a KDE-based desktop with Pop-like UX.

## v1 Scope: System Tasks
Focus on safe, high‑value system actions:
- Package install/remove
- System update
- Network toggles (Wi‑Fi/Bluetooth)
- Display/volume/brightness
- Power actions (sleep, reboot, shutdown)
- Open apps and URLs

## Interaction Style
- Natural English with a short confirmation step for risky actions.
- Provide spoken summaries of the action and impact.
- Friendly, conversational tone that feels like a helpful companion.

## Conversational Keep-Alive
For actions that may take a few seconds or minutes, keep the user engaged with short, reassuring filler lines so the experience never feels silent or stalled.
- Use brief, low-friction phrases like “Working on it” or “Almost there.”
- Avoid pretending an action completed if it hasn’t.
- If an action needs confirmation, ask clearly and offer a simple “confirm/cancel” path.

## Companion Persona
The assistant should feel like a helpful friend that gets to know the user over time.
- Warm and approachable, but not overly casual.
- Remembers user-provided facts when explicitly asked to “remember.”
- Offers short check-ins during longer tasks without being distracting.

## Examples
- "Install Firefox" -> `package_install` payload: `firefox`
- "Update the system" -> `system_update` payload: `stable`
- "Turn on Wi‑Fi" -> `network_wifi_on`
- "Set volume to 40%" -> `set_volume` payload: `40`
- "Restart the computer" -> `power_reboot` (confirm)
- "Check my Gmail" -> `open_url` payload: `https://mail.google.com/`
- "Open Firefox" -> `open_app` payload: `firefox`

## Confirmation Rules
- Required for:
  - package installs
  - system updates
  - power actions
- Denied by policy for destructive commands (see `policy.json`).

## Error Handling
- If intent cannot be mapped, respond with a clarification prompt.
- If policy denies action, explain the reason.

## Future Enhancements
- App navigation
- File actions
- Context-aware personalization
