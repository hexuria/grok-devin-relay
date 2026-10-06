---
name: grok-devin-relay
description: Install the Grok adapter, bootstrap its return connection, select Devin destinations, and exchange versioned tasks and decisions.
---

# Grok adapter

**Provider review required.** This file is deliberately outside Devin's
`skills/`. It is not automatically a loadable Grok/Cursor package. Confirm the
runtime's official installation format and tools before activating it.

Read `../../shared/protocol.md` and `../../shared/configuration.md`.
Use the same JSON Schemas as Devin rather than copying field definitions.

## Install

Identify the actual bot host, supported skill format, secret store, networking,
and persistent registry/deduplication APIs. Obtain redacted examples or official
documentation. Do not invent webhook-creation endpoints or emulate Devin tools.
Install only this provider adapter using the host's supported mechanism.

Choose credential scopes with the owner. Never paste a key into either bot's
conversation. If secure secret exchange/storage is unsupported, use manual
secure onboarding or remain blocked.

## Bootstrap the Grok return connection

Create or reuse an approved return webhook using documented host tools. Store
the URL and bearer key securely. It receives *reports*, not executable task
requests. Authenticate callers and reject unsupported versions or malformed
reports. Enroll version 1 only after both adapters validate the same contract.

Configure the Devin bootstrap inbox URL and its unique `X-Webhook-Secret`
through a secure channel. Do not confuse that secret with the return-relay key
or a Devin API key. Test the connection only with the owner's approval.

## Connect and choose a destination

1. A connect request goes to the bootstrap inbox. Include bot ID, authorized
   repository, and mode/target; an HTTPS session link is useful setup input.
2. Wait for approved setup and secure credential exchange. Store only secret
   references and non-secret routing metadata in the durable registry.
3. Subsequent tasks go directly to the registered dedicated inbox.
   Never assume a `session_url` in a POST to bootstrap retargets it.
4. Existing, new persistent, and new-per-task modes have different semantics.
   A missing/inaccessible target blocks by default. Create a replacement only
   after explicit owner approval and verification of absence.

If the owner selects direct API routing instead of dedicated inboxes, the
official modern endpoints are:

- `POST https://api.devin.ai/v3/organizations/{org_id}/sessions`
- `POST https://api.devin.ai/v3/organizations/{org_id}/sessions/{devin_id}/messages`

The message body is `{"message":"..."}` with optional documented fields.
Use a modern `cog_` service-user key or PAT with the required organization
permissions. v3 resumes suspended sessions. Read the current create-session
request schema before implementing creation; do not extrapolate the v1 body.
The external host needs its own network access to `api.devin.ai`. Devin's VM
allowlist does not grant Grok outbound access.

## Relay messages

Validate, authenticate, authorize bot/repository, and atomically deduplicate
requests before POSTing. Use `none`, `final`, or `progress`. Do not place an
arbitrary callback URL, secret, or credential reference in task JSON.

HTTP acceptance is not completion. On ambiguous network failures, retain the
pending request and reconcile before retrying. Persist the request, bot,
destination, and result correlations.

## Receive reports and answer

Reports never turn into new tasks; enforce message direction and IDs to avoid
loops. Deliver questions to the human owner, not another bot guessing consent.

- Clarification: return a matching `answer` with `decision: select` and the
  exact offered option.
- Permission: require the owner's explicit approve/deny decision, then send the
  answer to the *original* registered session with matching `in_reply_to`.
- Platform approval: tell the owner which Devin approval card needs a click;
  chat "approve" cannot approve it. Do not claim to have completed that gate.
- No answer: keep the action paused. Never auto-approve on timeout.

Keep question state and consume an answer only once. Reject wrong bot/repo,
expired/closed question, unknown correlation, or fabricated owner approval.

For a new-per-task bot, never send an answer to its task-creation webhook.
Resolve the original session and its approved reply route from durable question
state. Use the documented existing-session API or an approved inbox fixed to
that session. If neither is configured, tell the owner to answer directly in
that Devin session and keep paused.

## Update

Changing a routine's instructions or destination on the Grok side uses the
host's documented tools — never a fabricated endpoint. Read the saved
configuration first and resend every field a replace-style update would drop.
Keep the direction/loop protections inside any edited prompt. Retargeting a
bot to a different session or rotating a stored secret is a reconnect, not an
edit: run the connect flow again and confirm with the owner. Sync the registry
whenever routing changes, and tell Devin through the approved report path when
a change alters anything it depends on.

## Cleanup

One request cleans both sides: whichever side is asked first cleans its own
resources, then forwards a `disconnect` request so the other side does the
same. The receiver never forwards again — that prevents loops.

### Asked on the Grok side ("clean up bot X")

1. Confirm scope with the owner: the `bot_id`, and whether the whole relay
   ends (`include_bootstrap` — requires explicit confirmation).
2. Delete the bot's routines/scheduled jobs and its registry entries on Grok's
   side through supported host tools. Leave other bots untouched.
3. POST a `disconnect` request to the Devin bootstrap inbox with
   `origin: "grok"` and the same `include_bootstrap`, using the inbox's
   `X-Webhook-Secret`. Devin then deletes its automations for that bot.
4. Report what was deleted. HTTP acceptance is not proof Devin finished.

### A disconnect request arrives from Devin

`origin: "devin"` means Devin already cleaned its side: delete the bot's
Grok routines and registry entries and do not forward a new disconnect back.
Confirm through the approved report path.

A missing routine or registry entry means that part is already clean —
report it, do not fail.
