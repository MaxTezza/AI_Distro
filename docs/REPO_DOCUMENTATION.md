# AI Distro Repository Documentation

This document is a complete, file-by-file guide to what exists in this repo today. It focuses on what each file does, how the pieces connect, and what is currently scaffolded vs. functional.

## High-Level Overview
AI Distro is an Ubuntu-based, Pop-like KDE distribution built around a local, voice-first agent. The repo contains:
- Rust services for core, voice, and agent runtime.
- A local HTTP shell UI that drives the agent via IPC.
- Packaging and ISO scaffolding for Ubuntu 24.04 live-build.
- Configs for policy, intent parsing, and KDE theming.

## Runtime Components
- **ai-distro-agent**: IPC server and action executor. Handles natural language requests by invoking an intent parser.
- **ai-distro-core**: Core service placeholder for future system state and context orchestration.
- **ai-distro-voice**: Voice pipeline placeholder (ASR/TTS config wired, but processing is not implemented yet).
- **ai-distro-shell**: HTTP server + kiosk UI that sends commands to the agent.

## Build and Packaging Flow (Conceptual)
- `make build-rust` builds Rust binaries.
- `make stage-deb` stages binaries, configs, and UI into `build/deb-root/`.
- `make package-deb` wraps staged files into Debian packages.
- `make rootfs` invokes live-build to produce a squashfs rootfs.
- `make iso-build` creates the ISO staging directory.
- `make iso-assemble` produces the final ISO with boot assets if present.

## File Index

### Top-Level
- `README.md` — Short repo summary and doc pointers.
- `Makefile` — Build entry points for Rust, deb packaging, rootfs, and ISO.
- `CHANGELOG.md` — Empty placeholder.
- `CONTRIBUTING.md` — Empty placeholder.
- `CODE_OF_CONDUCT.md` — Empty placeholder.
- `SECURITY.md` — Empty placeholder.
- `ROADMAP.md` — Empty placeholder.
- `LICENSE` — Empty placeholder.
- `AGENTS.md` — Empty placeholder.

### Docs
- `docs/REPO_DOCUMENTATION.md` — This file.
- `docs/ARCHITECTURE.md` — Empty placeholder.
- `docs/API.md` — Empty placeholder.
- `docs/BOOT_ASSETS.md` — How boot assets are generated for ISO builds.
- `docs/CONFIGURATION.md` — Empty placeholder.
- `docs/CONTEXT.md` — Empty placeholder.
- `docs/CONVERSATIONAL_STYLE.md` — Companion tone and keep-alive behavior.
- `docs/DATA_MODEL.md` — Empty placeholder.
- `docs/DECISIONS.md` — Empty placeholder.
- `docs/DEPLOYMENT.md` — Empty placeholder.
- `docs/DESKTOP_UI.md` — Pop-like KDE UI and assistant overlay goals.
- `docs/INSTALLER.md` — Installer plan (Calamares, one-click install).
- `docs/IPC.md` — JSON-line IPC protocol for the agent.
- `docs/ISO_BOOT.md` — ISO boot assets and expected kernel/initrd paths.
- `docs/LEARNING.md` — Empty placeholder.
- `docs/MODEL_STRATEGY.md` — Empty placeholder.
- `docs/OPERATIONS.md` — Empty placeholder.
- `docs/PACKAGING.md` — Empty placeholder.
- `docs/PRIVACY.md` — Empty placeholder.
- `docs/ROOTFS_BUILD.md` — Rootfs build plan and references to live-build lists/hooks.
- `docs/RUNTIME_ENV.md` — Runtime environment variables.
- `docs/SECURITY_MODEL.md` — Empty placeholder.
- `docs/SKILLS.md` — Empty placeholder.
- `docs/TELEMETRY.md` — Empty placeholder.
- `docs/TESTING.md` — Empty placeholder.
- `docs/THREAT_MODEL.md` — Empty placeholder.
- `docs/VOICE_PIPELINE.md` — Empty placeholder.
- `docs/VOICE_STACK.md` — Voice engine choices and config references.
- `docs/VOICE_UX.md` — Voice-first UX scope and examples.

### Configs
- `configs/agent.json` — Agent service config (logging, policy, memory dir).
- `configs/core.json` — Core service config (state DB, IPC socket, context dir).
- `configs/intent-map.json` — Example-to-intent mapping for parsing.
- `configs/kdeglobals` — KDE defaults (Pop-like look and feel).
- `configs/persona.json` — Assistant persona and filler phrase configuration.
- `configs/persona.alfred.json` — Alfred-style persona preset.
- `configs/policy.json` — Policy enforcement rules for agent actions.
- `configs/voice.json` — Voice service config (ASR/TTS model and binaries).

### Rust Workspace
- `src/rust/Cargo.toml` — Workspace definition for all Rust crates.
- `src/rust/ai-distro-common/Cargo.toml` — Common library crate.
- `src/rust/ai-distro-common/src/lib.rs` — Shared config types and policy evaluation.
- `src/rust/ai-distro-core/Cargo.toml` — Core service crate.
- `src/rust/ai-distro-core/src/main.rs` — Core service stub (logs heartbeat).
- `src/rust/ai-distro-voice/Cargo.toml` — Voice service crate.
- `src/rust/ai-distro-voice/src/main.rs` — Voice service stub (logs config + heartbeat).
- `src/rust/ai-distro-agent/Cargo.toml` — Agent service crate.
- `src/rust/ai-distro-agent/src/main.rs` — Agent runtime, IPC server, handlers, confirmations.
- `src/rust/ai-distro-agent/src/bin/agent_client.rs` — Local client for IPC testing.

### Shell UI
- `assets/ui/shell/index.html` — Assistant shell layout and UI skeleton.
- `assets/ui/shell/styles.css` — Shell UI styling and animations.
- `assets/ui/shell/app.js` — Frontend logic to call agent and handle confirmations.
- `tools/shell/ai-distro-shell.sh` — Entrypoint for shell server.
- `tools/shell/ai-distro-shell-ui.sh` — Kiosk browser launcher for the shell UI.
- `tools/shell/ai_distro_shell.py` — HTTP server and IPC bridge.
- `tools/shell/ai_distro_shell.py` also serves persona presets for UI toggling.

### Intent Parsing
- `tools/agent/intent_parser.py` — Runtime intent parser invoked by the agent.
- `tools/dev/intent_parser.py` — Dev-only parser used by tests.
- `tools/dev/test_intent_parser.py` — Simple unit tests for the dev parser.
- `tools/dev/agent-ipc-client.py` — Minimal IPC client for manual testing.

### ISO and RootFS Build
- `src/infra/iso/README.md` — ISO build layout plan.
- `src/infra/iso/BUILD.md` — ISO staging flow and TODOs.
- `src/infra/rootfs/README.md` — Rootfs build overview.
- `src/infra/rootfs/live-build/README.md` — live-build layout and expectations.
- `src/infra/rootfs/live-build/BUILD.md` — Ubuntu 24.04 live-build notes.
- `src/infra/rootfs/live-build/auto/config` — live-build config command.
- `src/infra/rootfs/live-build/config/apt/sources.list.chroot` — Ubuntu noble apt sources.
- `src/infra/rootfs/live-build/config/package-lists/base.list.chroot` — Base packages.
- `src/infra/rootfs/live-build/config/package-lists/kde.list.chroot` — KDE packages.
- `src/infra/rootfs/live-build/config/package-lists/ai-distro.list.chroot` — AI Distro packages.
- `src/infra/rootfs/live-build/config/package-lists/voice.list.chroot` — Voice stack packages.
- `src/infra/rootfs/live-build/config/hooks/00-ai-distro.hook.chroot` — Placeholder rootfs hook.
- `src/infra/rootfs/live-build/config/hooks/10-ai-distro-packages.hook.chroot` — Installs local debs.
- `src/infra/rootfs/live-build/config/hooks/20-voice-stack.hook.chroot` — Best-effort voice deps install.
- `src/infra/rootfs/live-build/config/includes.chroot/ai-distro-packages/README.txt` — Where to drop debs.

### Bootloader
- `src/infra/boot/README.md` — Boot asset layout notes.
- `src/infra/boot/grub/grub.cfg` — GRUB live boot entry.

### Installer
- `src/infra/installer/README.md` — Installer overview and Calamares recommendation.
- `src/infra/installer/deb/README.md` — Debian/Ubuntu installer notes.
- `src/infra/installer/calamares/README.md` — Calamares scaffolding notes.
- `src/infra/installer/calamares/conf/settings.conf` — Calamares module sequence.
- `src/infra/installer/calamares/conf/modules.conf` — Module configurations.
- `src/infra/installer/calamares/branding/branding.desc` — Branding metadata.
- `src/infra/installer/calamares/scripts/ai-distro-postinstall` — Post-install enablement steps.

### Packaging (Debian)
- `src/infra/packaging/deb/README.md` — Packaging layout and notes.
- `src/infra/packaging/deb/BUILD.md` — Packaging build steps.
- `src/infra/packaging/deb/debian/control` — Debian package definitions.
- `src/infra/packaging/deb/debian/rules` — Debhelper rules.
- `src/infra/packaging/deb/debian/compat` — Debhelper compatibility level.
- `src/infra/packaging/deb/debian/changelog` — Package changelog.
- `src/infra/packaging/deb/debian/copyright` — Licensing metadata.
- `src/infra/packaging/deb/debian/source/format` — Source package format.
- `src/infra/packaging/deb/debian/ai-distro-core.install` — Install map for core.
- `src/infra/packaging/deb/debian/ai-distro-voice.install` — Install map for voice.
- `src/infra/packaging/deb/debian/ai-distro-agent.install` — Install map for agent.
- `src/infra/packaging/deb/debian/ai-distro-shell.install` — Install map for shell.
- `src/infra/packaging/deb/debian/ai-distro-core.dirs` — Directory stubs for dpkg.
- `src/infra/packaging/deb/systemd/ai-distro-core.service` — Core service unit.
- `src/infra/packaging/deb/systemd/ai-distro-voice.service` — Voice service unit.
- `src/infra/packaging/deb/systemd/ai-distro-agent.service` — Agent service unit.
- `src/infra/packaging/deb/systemd/ai-distro-agent.socket` — Agent IPC socket unit.
- `src/infra/packaging/deb/systemd/ai-distro-shell.service` — Shell server unit.
- `src/infra/packaging/deb/postinst/ai-distro-core` — Post-install core setup.
- `src/infra/packaging/deb/postinst/ai-distro-voice` — Post-install voice setup.
- `src/infra/packaging/deb/postinst/ai-distro-agent` — Post-install agent setup.
- `src/infra/packaging/deb/postinst/ai-distro-shell` — Post-install shell setup.
- `src/infra/packaging/deb/preinst/ai-distro-core` — Pre-install core hook.
- `src/infra/packaging/deb/preinst/ai-distro-voice` — Pre-install voice hook.
- `src/infra/packaging/deb/preinst/ai-distro-agent` — Pre-install agent hook.
- `src/infra/packaging/deb/prerm/ai-distro-core` — Pre-remove core hook.
- `src/infra/packaging/deb/prerm/ai-distro-voice` — Pre-remove voice hook.
- `src/infra/packaging/deb/prerm/ai-distro-agent` — Pre-remove agent hook.
- `src/infra/packaging/deb/postrm/ai-distro-core` — Post-remove core hook.
- `src/infra/packaging/deb/postrm/ai-distro-voice` — Post-remove voice hook.
- `src/infra/packaging/deb/postrm/ai-distro-agent` — Post-remove agent hook.
- `src/infra/packaging/deb/polkit/ai-distro.policy` — Polkit policy stub.
- `src/infra/packaging/deb/apparmor/ai-distro-core` — AppArmor profile stub.
- `src/infra/packaging/deb/logrotate/ai-distro` — Logrotate configuration.
- `src/infra/packaging/deb/udev/99-ai-distro.rules` — Placeholder udev rules.
- `src/infra/packaging/deb/xdg/ai-distro-shell.desktop` — Autostart entry for shell UI.

### Build Tools
- `tools/build/build-rust.sh` — Cargo build wrapper.
- `tools/build/stage-deb.sh` — Stages deb root filesystem.
- `tools/build/package-deb.sh` — Builds debs from staged files.
- `tools/build/deps.sh` — Installs build dependencies.
- `tools/build/rootfs-build.sh` — live-build rootfs orchestration.
- `tools/build/iso-build.sh` — ISO staging directory build.
- `tools/build/boot-assets.sh` — GRUB BIOS/UEFI boot assets.
- `tools/build/iso-assemble.sh` — Final ISO assembly with xorriso.
- `tools/build/vm-test.sh` — QEMU boot smoke test.

### Theme Assets
- `assets/themes/ai-distro/metadata.json` — KDE look-and-feel metadata.
- `assets/themes/ai-distro/contents/defaults` — KDE defaults scaffold.
- `assets/themes/ai-distro/contents/color-schemes/AI-Distro.colors` — Theme colors.

## Known Scaffolds and Gaps
- Many docs are empty placeholders and need content.
- The Rust core and voice services are stubs (heartbeat-only).
- ISO and rootfs build are wired but still rely on live-build setup and kernel/initrd artifacts.
- Calamares branding assets (logo/background) are not present.
