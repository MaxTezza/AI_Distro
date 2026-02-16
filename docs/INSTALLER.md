# Installer Plan (ISO)

## Goal
Provide a one‑click install experience via a bootable ISO image.

## Approach
- Build a live ISO with a graphical installer.
- One‑click path uses default partitioning and installs AI Distro with KDE + Pop‑like theme + services enabled.

## Components
- `src/infra/iso/` for ISO build assets
- `src/infra/installer/` for installer configs and hooks
- `src/infra/boot/` for bootloader config (GRUB)

## Next Steps
- Choose installer base: Calamares (recommended for GUI) or Subiquity/Ubuntu Desktop.
- Define default partitioning and post‑install hooks.
- Bundle packages: core/voice/agent + KDE + theme + configs.
