#!/bin/sh
set -e

ROOT="${1:-/home/jmt3/AI_Distro/build/deb-root}"
ROOT_DIR="/home/jmt3/AI_Distro"

rm -rf "$ROOT"
mkdir -p "$ROOT/usr/bin" "$ROOT/etc/ai-distro" "$ROOT/lib/systemd/system" \
  "$ROOT/var/lib/ai-distro" "$ROOT/var/log/ai-distro" \
  "$ROOT/usr/lib/ai-distro" "$ROOT/usr/share/ai-distro" "$ROOT/etc/xdg/autostart"

# Build Rust binaries
"$ROOT_DIR/tools/build/build-rust.sh"

# Binaries
cp "$ROOT_DIR/src/rust/target/release/ai-distro-core" "$ROOT/usr/bin/ai-distro-core"
cp "$ROOT_DIR/src/rust/target/release/ai-distro-voice" "$ROOT/usr/bin/ai-distro-voice"
cp "$ROOT_DIR/src/rust/target/release/ai-distro-agent" "$ROOT/usr/bin/ai-distro-agent"

# Systemd units
cp "$ROOT_DIR/src/infra/packaging/deb/systemd/ai-distro-core.service" "$ROOT/lib/systemd/system/ai-distro-core.service"
cp "$ROOT_DIR/src/infra/packaging/deb/systemd/ai-distro-voice.service" "$ROOT/lib/systemd/system/ai-distro-voice.service"
cp "$ROOT_DIR/src/infra/packaging/deb/systemd/ai-distro-agent.service" "$ROOT/lib/systemd/system/ai-distro-agent.service"
cp "$ROOT_DIR/src/infra/packaging/deb/systemd/ai-distro-agent.socket" "$ROOT/lib/systemd/system/ai-distro-agent.socket"
cp "$ROOT_DIR/src/infra/packaging/deb/systemd/ai-distro-shell.service" "$ROOT/lib/systemd/system/ai-distro-shell.service"

# Shell server + UI
cp "$ROOT_DIR/tools/shell/ai-distro-shell.sh" "$ROOT/usr/bin/ai-distro-shell"
cp "$ROOT_DIR/tools/shell/ai-distro-shell-ui.sh" "$ROOT/usr/bin/ai-distro-shell-ui"
cp "$ROOT_DIR/tools/shell/ai_distro_shell.py" "$ROOT/usr/lib/ai-distro/ai_distro_shell.py"
cp -r "$ROOT_DIR/assets/ui/shell" "$ROOT/usr/share/ai-distro/ui"
cp "$ROOT_DIR/src/infra/packaging/deb/xdg/ai-distro-shell.desktop" "$ROOT/etc/xdg/autostart/ai-distro-shell.desktop"

# Intent parser
cp "$ROOT_DIR/tools/agent/intent_parser.py" "$ROOT/usr/lib/ai-distro/intent_parser.py"
cp "$ROOT_DIR/tools/agent/day_planner.py" "$ROOT/usr/lib/ai-distro/day_planner.py"
cp "$ROOT_DIR/tools/agent/google_calendar_oauth.py" "$ROOT/usr/lib/ai-distro/google_calendar_oauth.py"
cp "$ROOT_DIR/tools/agent/weather_tool.py" "$ROOT/usr/lib/ai-distro/weather_tool.py"
cp "$ROOT_DIR/tools/agent/calendar_tool.py" "$ROOT/usr/lib/ai-distro/calendar_tool.py"

echo "Staged Debian root at $ROOT"
