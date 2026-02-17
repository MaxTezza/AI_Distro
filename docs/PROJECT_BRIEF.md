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
  - Calendar: `local`, `google`, `microsoft`
  - Email: `gmail`, `outlook`, `imap` (IMAP enables Proton Bridge compatibility)
- No-code provider setup is now live in shell UI:
  - Connect/Test flows in Settings panel
  - OAuth callback auto-capture (`/oauth/callback`) with automatic token exchange
  - No manual code paste required in normal path
- Natural-language app package flow is now live:
  - `install <app>`, `uninstall/remove <app>`, `update my apps`
  - Automatic source routing (`flatpak` first when resolvable, fallback to `apt`)
  - Ambiguity prompts for unclear app matches
- Shell now includes:
  - Conversational progress messaging during task execution
  - App Tasks status/history panel backed by audit events
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

1. Package execution safety + privilege UX:
   - Route privileged package actions through confirmation + privileged executor path (no raw lock/permission errors).
   - Add preflight summaries before execution (source, resolved package/app id, action impact).
2. OAuth no-code hardening:
   - Persist provider connect session state safely across shell restarts.
   - Add timeout/retry UX and clearer reconnect flows.
3. App resolution quality:
   - Expand alias catalog and deterministic ranking.
   - Add “app not found” alternative suggestions with plain-language follow-up.
4. Real-user acceptance suite:
   - Add non-technical task checks (install app, connect account, run daily workflow) and track completion friction.
5. Release prep:
   - VM smoke + installer flow checks aligned with no-code UX goals.
   - Final copy polish pass for conversational status and failure recovery.

## Plan For Completion

1. Complete privileged package execution path
   - Deliverable: package install/remove/update flows never surface low-level permission/lock errors to user.
   - Validation: end-to-end command tests in shell + audit outcome checks.
2. Finish no-code provider onboarding
   - Deliverable: OAuth connect succeeds from single Connect action with robust retry/recover behavior.
   - Validation: Google + Microsoft connect/disconnect/reconnect scenarios.
3. Improve app discovery confidence
   - Deliverable: high-confidence mapping for top requested apps and safe clarification flow for ambiguous names.
   - Validation: expanded parser/resolver test set + live shell command pass.
4. Run usability-focused QA
   - Deliverable: scripted user journeys for new users with target completion and error-recovery thresholds.
   - Validation: recorded pass checklist before release candidate.
5. Cut release candidate
   - Deliverable: clean QA gate, VM install smoke pass, updated docs/handoff for RC.
   - Validation: one-command quality gate + installer verification checklist.

## Release Quality Bar

- Top 20 task pass rate: >= 95%
- Dangerous actions require confirmation: 100%
- Zero unconfirmed destructive actions
- VM boot smoke test passes before demo/release

## Handoff Notes for New Agents

- Current baseline commit: `05582b1` on `main` (local/remote synced).
- First commands on new session:
  1. `cd /home/jmt3/AI_Distro`
  2. `git pull --ff-only`
  3. `make qa-voice`
- Start with `docs/TOP20_TASKS.md` and `docs/VOICE_ACCEPTANCE.md`.
- Do not weaken confirmation policy to boost pass rates.
- Prefer user-visible reliability and provider-agnostic action surfaces over provider-specific voice commands.
- Keep changes measurable with automated checks.
