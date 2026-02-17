# Immutable OS Architecture

To ensure AI Distro is robust, "unbreakable," and easy to reset, we are adopting an **Immutable A/B Partition** architecture.

## Overview
The core operating system (kernel, systemd, desktop environment, AI agent) resides in a **Read-Only** partition. User data (documents, settings, installed Flatpaks) resides in a separate **Read-Write** partition.

## Partition Layout

| Partition | Label | FS | Role |
|---|---|---|---|
| 1 | `EFI` | vfat | Bootloader (GRUB/Systemd-boot) |
| 2 | `ROOT_A` | ext4/squashfs | Active System Root (Read-Only) |
| 3 | `ROOT_B` | ext4/squashfs | Passive System Root (For Updates) |
| 4 | `DATA` | ext4/btrfs | User Home (`/home`), Logs (`/var/log`), Containers |

## Boot Process
1.  Bootloader checks which partition (`ROOT_A` or `ROOT_B`) is flagged as "Active".
2.  Kernel boots with `root=/dev/disk/by-label/ROOT_A ro`.
3.  `systemd` mounts `DATA` partition to `/home` and `/var/lib/ai-distro`.
4.  OverlayFS is used for `/etc` to allow transient configuration changes if necessary.

## Update Mechanism (Atomic)
The traditional `apt-get upgrade` is disabled for the core system to prevent breakage.

**New Workflow:**
1.  Agent downloads the new system image (`system.img`).
2.  Agent writes `system.img` to the **Passive Partition** (e.g., `ROOT_B`).
3.  Agent updates the Bootloader config to set `ROOT_B` as "Next Boot".
4.  Reboot.
5.  If boot succeeds, `ROOT_B` becomes "Active". If it fails, Watchdog reverts to `ROOT_A`.

## User Applications
Users install apps via **Flatpak** or **Distrobox** containers, which live in the `DATA` partition. This keeps user software isolated from the system core.
