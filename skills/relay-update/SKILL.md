---
name: relay-update
description: Change an existing relay webhook's instructions, target session, networking, grants, or other details on Devin — with owner approval.
---

# Update a relay webhook

Use only in Devin. Read `../../shared/protocol.md` and
`../../shared/configuration.md`. Invoke builtin `managing-automations`.

## Asked in a Devin chat ("update bot X's webhook", "change the instructions")

1. Find the automation: `list`, then `get` each candidate, matching on
   `bot_id` / `relay_role` metadata — never on the name alone.
2. Read the saved configuration and pin down exactly which fields change:
   instructions/prompt, target session, `auto_create`, network policy,
   tool/MCP grants, notifications, limits, enabled flag, metadata.
   Update is PATCH — omitted fields stay unchanged, and `schemas` says
   whether each passed group merges or replaces. When a group replaces,
   resend every member you want to keep.
3. Editing the instructions: copy the text between the `BEGIN/END PROMPT`
   markers into a local file, edit it, and resend the full `actions` array
   with `"prompt": "file:///absolute/path"`. Never retype a long prompt, and
   never lose the direction/loop protections or response policy inside it.
4. `validate_update` the exact payload and fix every reported problem, then
   `update` — the approval card is the owner's review of the change.
5. `get` the automation and verify what was actually saved. Sync the
   registry entry whenever the change alters routing (new target session,
   new mode, new inbox).

## Not an update — recreate instead

- Switching the session mode (`existing` → `new_persistent`, etc.) or the
  action type is fixed at creation: run `relay-connect-session` for the new
  setup, then `relay-cleanup` for the old automation.
- A leaked or rotated `X-Webhook-Secret` cannot be changed through the
  automation tools: rotate it in the automation's editor in the webapp, or
  recreate the inbox.
- Changing which session a bot reaches is a retarget — treat it like a new
  connect and confirm with the owner explicitly.

## Rules

- Never silently retarget a bot's destination or widen its network access —
  those changes always need explicit owner confirmation.
- Real session IDs, URLs, and secrets never go into prompts or metadata;
  keep using `secret:...` references and let the session resolve them.
- If the change alters anything the other side depends on (inbox URL,
  secret, response policy), say so through the approved report path — an
  update on this side is invisible over there.
- `update` never creates: if `get` finds nothing, the answer is
  `relay-connect-session` or `relay-cleanup`, not an update.
