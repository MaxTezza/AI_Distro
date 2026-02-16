# Debian Packaging

This folder contains Debian packaging scaffolding for AI Distro.

## Layout
- `debian/` control files
- `systemd/` unit files
- `polkit/`, `udev/`, `apparmor/` policy stubs
- `postinst/`, `prerm/`, `postrm/`, `preinst/` maintainer scripts

## Build
Use `make stage-deb` to assemble the staged root.
See `BUILD.md` for packaging steps.
