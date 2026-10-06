# Grok ↔ Devin relay

One repository, one shared contract, two adapters. Devin skills live under
`skills/` (loaded by `.devin-plugin/`); the Grok adapter lives under
`providers/grok/`. The relay lets Grok bot send tasks into Devin sessions and
receive reports back — including permission questions that stay paused until
the owner answers.

## Getting started

Each step maps to one skill. Run them in order.

| Step | Skill | What it does |
|---|---|---|
| 1 | `relay-install` | Verify secrets, integrations, and network policy. Creates nothing. |
| 2 | `relay-bootstrap-devin` | Create the ONE control-plane webhook automation. Grok posts setup requests here. |
| 3 | `providers/grok/SKILL.md` | Install Grok's adapter on its side and bootstrap its return relay. |
| 4 | `relay-connect-session` | Connect a bot to a Devin session — existing, new-persistent, or new-per-task — by creating a dedicated webhook. |
| 5 | `relay-message` + `grok-relay-report` | Handle tasks in the session; send reports and questions back to Grok. |
| — | `relay-cleanup` | Remove a bot's automations and registry entries on Devin plus its routines on Grok — one chat request cleans both sides. |

## Walkthrough

1. **In Devin:** ask to install this repo as a plugin → `relay-install`
   verifies the environment.
2. **In Devin:** bootstrap → `relay-bootstrap-devin` creates the
   control-plane webhook automation (with approval cards).
3. **Grok** sends a connect request to the bootstrap webhook, naming the bot,
   the allowed repo, and the target session:

   ```json
   {
     "protocol_version": "1",
     "request_id": "connect-001",
     "operation": "connect",
     "bot_id": "pua-review",
     "repo": "hexuria/pua",
     "session": {
       "mode": "existing",
       "target": "https://app.devin.ai/sessions/00000000000000000000000000000001",
       "if_missing": "block"
     }
   }
   ```

4. The control plane runs `relay-connect-session` and — after approval —
   creates a dedicated webhook automation for that bot, pointing at that
   session. Its URL and secret go into approved secret storage; the registry
   records bot → destination.
5. **Grok** now POSTs tasks to that dedicated webhook:

   ```json
   {
     "protocol_version": "1",
     "request_id": "task-001",
     "operation": "task",
     "bot_id": "pua-review",
     "repo": "hexuria/pua",
     "task": "Open a PR that fixes the flaky test",
     "response_mode": "final"
   }
   ```

6. The session runs `relay-message`, does the work, and reports through the
   return relay via `grok-relay-report`. Permission questions pause until the
   owner answers — silence is never approval.
7. Done with a bot? Say "clean up `pua-review`" in a Devin or Grok chat →
   `relay-cleanup` deletes its automations and routines on both sides.

## The one routing rule that matters

A webhook has a fixed destination. A session link inside a task POST body
does **not** retarget it — the connect step is what binds a bot to a session.
To reach a different session, connect again or use the v3 session-messages API.

## Layout

- `skills/` — Devin plugin skills (manifest: `.devin-plugin/plugin.json`)
- `providers/grok/` — Grok-side adapter (outside Devin's skills on purpose)
- `shared/` — `protocol.md`, `configuration.md`, JSON Schemas (request/report/registry)
- `examples/` — synthetic fixtures and disabled automation templates
- `CONTRIBUTING.md` — development setup and offline checks
- `VERIFICATION.md` — what has and has not been verified

## Status

Offline-verified: contract tests, lint, and type checks pass (see
`CONTRIBUTING.md`). No live webhook round-trip has been exercised and Grok's
runtime is unconfirmed — open questions for Grok are in `GROK-REVIEW.md`.
