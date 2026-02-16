#!/bin/sh
set -e

URL="${AI_DISTRO_SHELL_URL:-http://127.0.0.1:17842/}"

find_browser() {
  for b in chromium chromium-browser google-chrome-stable google-chrome firefox; do
    if command -v "$b" >/dev/null 2>&1; then
      echo "$b"
      return 0
    fi
  done
  return 1
}

BROWSER="$(find_browser || true)"
if [ -z "$BROWSER" ]; then
  echo "No supported browser found (chromium/firefox)." >&2
  exit 1
fi

case "$BROWSER" in
  chromium|chromium-browser|google-chrome|google-chrome-stable)
    exec "$BROWSER" --kiosk --app="$URL" --start-fullscreen --no-first-run --use-fake-ui-for-media-stream
    ;;
  firefox)
    exec "$BROWSER" --kiosk "$URL"
    ;;
  *)
    exec "$BROWSER" "$URL"
    ;;
esac
