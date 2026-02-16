# ISO Boot Assets (Scaffold)

## GRUB
`src/infra/boot/grub/grub.cfg` contains a basic live boot entry.

Expected kernel/initrd paths (adjust as rootfs layout is finalized):
- `/casper/vmlinuz`
- `/casper/initrd`

## EFI / BIOS
Place EFI assets under `src/infra/boot/efi/` and legacy BIOS assets under `src/infra/boot/syslinux/`.

## Next Steps
- Populate EFI bootloader assets
- Wire correct kernel/initrd from live-build output
- Update ISO assembly with proper boot options
