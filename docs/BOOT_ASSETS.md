# Boot Assets Generation

## Script
`tools/build/boot-assets.sh`

## Requirements
- `grub-mkimage` (from `grub-pc-bin` and `grub-efi-amd64-bin`)

## Usage
Generate boot assets in the ISO staging directory:

  AI_DISTRO_BOOT_ASSETS=1 tools/build/iso-build.sh

This will create:
- BIOS El Torito image: `build/iso/boot/grub/i386-pc/eltorito.img`
- EFI bootloader: `build/iso/EFI/BOOT/BOOTX64.EFI`
