---
name: relay-connect-session
description: Connect an approved Grok bot to an existing Devin session, a new persistent session, or a new-session-per-task webhook.
---

# Connect a bot to a session

Use only in Devin. Read `../../shared/protocol.md` and
`../../shared/configuration.md`. Invoke builtin `managing-automations`.

1. Authenticate the owner/request origin using the host's trusted context.
   Validate the version-1 connect request with `shared/schemas/request.schema.json`.
   Resolve the bot through the approved persistent registry, not a similarly
   named automation or an incoming secret/callback field.
2. Normalize an existing session link or ID. Accept only an HTTPS
   `app.devin.ai/sessions/<32 lowercase hex>` link or a canonical
   `devin-<32 lowercase hex>` ID. Verify organization membership and access
   through native Devin session tools. Never execute a payload-supplied URL.
3. Choose the requested mode:
   - `existing`: `message_session`, explicit target, `auto_create: false`.
   - `new_persistent`: `message_session`, `auto_create: true`, no initial target.
   - `new_per_task`: `start_session` with enough context for an isolated run.
4. `if_missing: create_after_owner_approval` is not automatic fallback.
   Confirm actual absence and ask the owner before replacing a target.
   Never create on 401/403, hidden access, timeout, or 5xx. Sleeping is not
   missing. `auto_create` is not a generic recovery flag for invalid targets.
5. List/get to find an already approved matching connection. If bot ID,
   repository authorization, target, or mode conflicts, ask rather than
   silently retargeting or duplicating. Unknown bot IDs require enrollment;
   a request's `bot_id` is a selector, not proof of permission.
6. Read live schemas and integrations. Prepare a separate `webhook:incoming`
   automation; keep the first/bootstrap webhook intact. Include the approved
   repository, versioned response policy, secret references, and direction/loop
   protections in instructions. Choose identity, MCP grants, networking,
   notifications, and limits using the configuration guide.
7. Validate the exact payload, propose it for native approval, then inspect the
   approval result and saved configuration. Do not send the original task to
   the new destination before setup is verified.
8. Store the inbox URL and its unique `X-Webhook-Secret` in supported secret
   storage. Store only references in the registry. Secure exchange is required;
   if unsupported, pause for the owner's manual secure onboarding.
9. Register mode/automation/session ID after successful setup. For a new
   persistent bot, retain `session_id: null` until the first trigger yields the
   real target; retrieve it with native tools, then atomically update the
   registry. A guessed or synthetic ID is never a successful connection.
10. Report a non-secret connection result with bot ID and real session URL when
    available. Transport acceptance is not proof the target executed the task.

For new-per-task bots, establish how answers reach the original task session:
the documented v3 message API or a separately approved fixed-session inbox.
Do not reuse the task-creation webhook for answers. Without an approved answer
transport, questions require the owner's direct reply in that Devin session.

A direct v3 API router is an alternative on Grok's external integration host.
Inside Devin, use native resource-management tools, not guessed API credentials.
