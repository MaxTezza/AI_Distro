# Desktop UI (KDE + Pop‑like)

## Goal
Deliver a KDE Plasma experience styled and laid out to feel similar to Pop!_OS.
The default experience boots into a full-screen AI assistant overlay that can be dismissed for manual control.

## Layout
- Left dock (launcher + pinned apps)
- Top bar (status + workspace controls)
- Tiling enabled (KWin scripts / built‑in tiling)

## Theme Direction
- Dark-neutral base with high contrast accents
- Flat icon set, minimal chrome
- Clear visual hierarchy

## Components
- **Launcher:** Kickoff or application menu with search‑first UI
- **Dock:** Latte Dock (or Plasma Panel) configured for vertical layout
- **Tiling:** KWin tiling scripts or built‑in tiling behavior
- **Assistant Shell:** Full-screen overlay UI (ai-distro-shell) launched at login

## Conversational Experience
The assistant overlay should avoid long silent periods during tasks. When actions take time:
- Show lightweight, friendly filler messages to confirm progress.
- Keep the user informed without over-explaining.
- Maintain a consistent, companion-like tone.

## Packaging Hooks
- Install theme assets into `/usr/share` or `/usr/local/share`
- Set defaults with KDE config files in `/etc/xdg`

## Future
- Optional COSMIC‑style animation theme
- Custom system settings module for AI features
