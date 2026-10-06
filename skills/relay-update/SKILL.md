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
2. Read the saved configuration and use this UI-field checklist:
   Name (`name`), Active toggle (`enabled`), Trigger: Webhook
   (`triggers[].event_type`), Secret (`X-Webhook-Secret`; editor-only
   rotation), Payload filter (editor-only), Agent type
   (`actions[].type`), Destination session (`target_devin_id`, `auto_create`),
   Instructions (`actions[].prompt`), Agent mode (`session_settings.devin_mode`),
   Run as (`run_as.type`), MCPs (`tools`), Notifications (`notifications`),
   Shared scratchpad (editor-only), Network policy
   (`session_settings.net_policy`), Metadata (`metadata`), Spend limit
   (`limits.max_acu_limit`), Rate limit (`limits.invocations`), Concurrent
   runs (`concurrency.max_concurrent_runs`), Queue depth
   (`concurrency.max_queue_depth`), and Security profile (owner-selected).
   Payload filter, Shared scratchpad, and Secret rotation are editor-only:
   tell the owner to change the Payload filter, Shared scratchpad (Advanced)
   toggle, or webhook Secret rotate control in the automation editor.
   Update is merge-patch: omitted top-level parameters and omitted keys within
   a passed group stay unchanged, `null` clears a key, and lists replace
   wholesale. Resend every list entry you want to keep. See
   `../../shared/configuration.md` for details.
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
