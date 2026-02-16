# Project Brief

## Mission

Build a voice-first personal computer experience that feels easier than Windows for non-technical users.

The product goal is not "a Linux distro for engineers."  
The goal is "regular people can talk naturally to their machine and it gets things done across apps."

## Product Feel (Non-Negotiable)

- Voice interaction should feel clear, calm, and predictable.
- The system should always reflect intent before risky actions.
- The user should never need terminal knowledge for normal tasks.
- The assistant should remember useful user context only when explicitly asked.
- Cross-app workflows matter more than distro internals.

## Current Milestone Status

- Bootable ISO works in VM.
- Voice parser and Top 20 task gate are implemented.
- Automated QA exists locally and in GitHub Actions.

Run the core gate:

```bash
cd /home/jmt3/AI_Distro
make qa-voice
```

## Top Priorities (Next)

1. Onboarding Wizard v1
2. End-to-end voice UX polish ("I heard / I will do")
3. Memory management UI (view/edit/delete)
4. App integration depth for daily workflows

## Release Quality Bar

- Top 20 task pass rate: >= 95%
- Dangerous actions require confirmation: 100%
- Zero unconfirmed destructive actions
- VM boot smoke test passes before demo/release

## Handoff Notes for New Agents

- Start with `docs/TOP20_TASKS.md` and `docs/VOICE_ACCEPTANCE.md`.
- Do not weaken confirmation policy to boost pass rates.
- Prefer user-visible reliability over adding new low-value commands.
- Keep changes measurable with automated checks.
