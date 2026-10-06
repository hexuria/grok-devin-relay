---
name: relay-cleanup
description: Tear down a relay bot's Devin webhook automations and registry entries, and trigger the matching cleanup on the Grok side — from one chat request on either side.
---

# Clean up a relay bot

Use only in Devin. Read `../../shared/protocol.md` and
`../../shared/configuration.md`. Invoke builtin `managing-automations`.

One request cleans both sides: whichever side is asked first cleans its own
resources, then forwards a `disconnect` request so the other side does the
same. The receiver never forwards again — that is what prevents loops.

## Asked in a Devin chat ("clean up bot X")

1. Confirm scope with the owner before deleting anything: the `bot_id`, and
   whether the bootstrap inbox goes too (`include_bootstrap`). Removing the
   bootstrap inbox ends the whole relay for every bot — require explicit
   confirmation for that.
2. List automations and find the bot's dedicated inboxes by their
   `bot_id` / `relay_role` metadata. Skip `triage_session` and code-scan
   automations (`start_code_scan`, `scan_new_commits`); they are not relay
   destinations. Never match by name alone and never touch unrelated
   automations.
3. Delete each matching automation through native approval (`delete`).
4. Remove the bot's registry entry; leave every other bot untouched. With
   `include_bootstrap`, also delete the bootstrap automation and its
   registry/configuration entries.
5. Forward a `disconnect` request to the Grok return relay with
   `origin: "devin"` and the same `include_bootstrap` value, so Grok deletes
   its routines and registry entries. If the relay is unreachable, say so —
   the Devin-side cleanup is still done.
6. Report what was deleted through the approved report path and
   `message_user`.

## A disconnect request arrives through the bootstrap inbox

1. Authenticate the sender, validate against `request.schema.json`, and
   resolve the bot in the registry.
2. `origin` tells you which side already cleaned: `grok` means Grok is done
   and you clean only the Devin side. Do not forward a new disconnect back —
   the loop ends here.
3. Delete the bot's Devin resources exactly as above (and the bootstrap
   automation only when `include_bootstrap` is true — note that this inbox is
   then gone too, so send the report before deleting it).
4. Report `done` or `blocked` through the approved relay path.

## Rules

- Never delete anything silently — scope is confirmed with the owner first.
- Never let a body field widen the scope beyond the requested bot.
- HTTP acceptance is not proof the other side cleaned up; report what this
  side actually deleted and mark the other side's result separately.
- A missing registry entry or automation means it is already clean — report
  that, do not fail.
