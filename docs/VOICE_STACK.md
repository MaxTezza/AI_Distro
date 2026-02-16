# Voice Stack (v1)

## Goals
- Offline ASR for natural English
- Local TTS for audible feedback
- Pluggable engines (config‑driven)

## Recommended v1 Engines
- **ASR:** Vosk (offline, lightweight)
- **TTS:** Piper (fast, local neural TTS)

## Notes
- Whisper offers higher accuracy but heavier CPU/GPU usage.
- Piper can be installed via snap or pip depending on packaging strategy.

## Config Integration
See `configs/voice.json` for engine selection and binary paths.

## Packaging Notes
The rootfs build attempts to install `vosk` and `piper` packages when available.
Adjust package names per Ubuntu repository availability.
