# ISO Build (Scaffold)

## Inputs
- Calamares configs: `src/infra/installer/calamares/`
- Root filesystem squashfs (to be generated)

## Staging
Run:

  tools/build/iso-build.sh

This creates:

- `build/iso/` — staging directory
  - `calamares/` — installer configs
  - `rootfs/` — placeholder for rootfs.squashfs
  - `boot/` — placeholder for bootloader config

## TODO
- Build rootfs from base system + AI Distro packages
- Add GRUB/EFI boot assets
- Generate final ISO via `xorriso` or `mkisofs`
