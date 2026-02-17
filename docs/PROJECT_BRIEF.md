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
- Onboarding Wizard v1 is implemented with resume/replay.
- Agent safety baseline is in place: confirmations, policy allowlists, rate limits, and hash-chained audit logs.
- Provider-router architecture is live for integrations (calendar/email).
- Calendar and email integrations now support multiple providers:
  - Calendar: `local`, `google` (router-ready for Microsoft)
  - Email: `gmail`, `outlook`, `imap` (IMAP enables Proton Bridge compatibility)
- Voice actions now include:
  - `weather_get`
  - `calendar_list_day`
  - `calendar_add_event` (confirmation-gated)
  - `plan_day_outfit` (weather + calendar)
  - `email_inbox_summary`
  - `email_search`
  - `email_draft` (confirmation-gated)

Run the core gate:

```bash
cd /home/jmt3/AI_Distro
make qa-voice
```

## Top Priorities (Next)

1. Microsoft Calendar provider plugin (read/list first, then add-event write path with confirmation)
2. Outlook draft support so `email_draft` works across `gmail` + `outlook` + future providers
3. QA security gate (`verify_audit_chain`) wired into CI and one-command local gate
4. Voice UX polish ("I heard / I will do" + clearer failure recovery copy)

## Release Quality Bar

- Top 20 task pass rate: >= 95%
- Dangerous actions require confirmation: 100%
- Zero unconfirmed destructive actions
- VM boot smoke test passes before demo/release

## Handoff Notes for New Agents

- Current baseline commit: `892392b` on `main` (local/remote synced at handoff time).
- First commands on new session:
  1. `cd /home/jmt3/AI_Distro`
  2. `git pull --ff-only`
  3. `make qa-voice`
- Start with `docs/TOP20_TASKS.md` and `docs/VOICE_ACCEPTANCE.md`.
- Do not weaken confirmation policy to boost pass rates.
- Prefer user-visible reliability and provider-agnostic action surfaces over provider-specific voice commands.
- Keep changes measurable with automated checks.
