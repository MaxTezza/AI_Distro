# RootFS Build (Phase A)

## Goal
Create a KDE-based root filesystem with AI Distro services installed.

## Recommended Tooling
- `live-build` (Debian) or `debootstrap`

## Package Lists
- `src/infra/rootfs/live-build/config/package-lists/base.list.chroot`
- `src/infra/rootfs/live-build/config/package-lists/kde.list.chroot`
- `src/infra/rootfs/live-build/config/package-lists/ai-distro.list.chroot`

## Hooks
- `src/infra/rootfs/live-build/config/hooks/00-ai-distro.hook.chroot`

## Output
- `build/rootfs/rootfs.squashfs`

## Next Steps
- Choose base distribution and mirror
- Implement live-build config under `src/infra/rootfs/live-build/`
