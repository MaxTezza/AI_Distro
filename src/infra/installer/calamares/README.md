# Calamares Installer (Scaffold)

This directory contains initial Calamares configuration for AI Distro.

## Files
- `conf/settings.conf` — module sequence
- `conf/modules.conf` — per-module config
- `branding/branding.desc` — branding metadata
- `scripts/ai-distro-postinstall` — post-install hook

## Next Steps
- Add branding assets under `branding/` (logo, background)
- Wire post-install steps to enable services and apply KDE defaults
- Integrate into ISO build pipeline
