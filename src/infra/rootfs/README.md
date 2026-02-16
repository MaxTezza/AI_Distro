# RootFS Build

This folder contains root filesystem build scaffolding.

## Recommended Tool
Use `live-build` or `debootstrap` to create the base rootfs.

## Layout
- `live-build/` live-build config skeleton

## Output
RootFS artifacts should be placed under `build/rootfs/`:
- `rootfs.squashfs`

## Next Steps
- Define the base distribution and mirror
- Update live-build package lists and hooks
