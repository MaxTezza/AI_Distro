# Debian Build Workflow

## Prereqs
- debhelper (compat 13)
- dpkg-dev
- Rust toolchain (cargo)

## Build

  make build-rust

Builds release binaries for core, voice, and agent.

## Staging

  make stage-deb

Stages files into `build/deb-root/`.

## Packaging

  make package-deb

This creates a minimal source tree in `build/deb-src/`, copies the `debian/`
metadata, and runs:

  dpkg-buildpackage -b -us -uc

from that build directory.
