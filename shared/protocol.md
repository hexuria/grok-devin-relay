# Shared protocol, version 1

Paths in skill examples such as `shared/schemas/` are relative to the plugin
root; Markdown links in documents are relative to the document.

This is the common contract for both adapters. The host must provide
authentication, authorization, durable routing, atomic deduplication, secure
credential storage, and approved transport. A skill alone provides none of them.

## Control plane and data plane

The bootstrap inbox receives `bootstrap` or `connect` requests. It prepares
resources asynchronously; a webhook HTTP response is not the created endpoint.
An owner-approved persistent registry maps bot IDs to dedicated destinations.

An existing/persistent dedicated inbox receives `task` or `answer`; a
new-per-task inbox receives **tasks only**. Its configured automation
determines the target. Session links in connect requests are setup data, not
native routing fields. The registry must match trusted sender/organization and
allowed repositories before any task executes.

Version-1 wire schemas:

- [Request](schemas/request.schema.json): bootstrap/connect/task/answer
- [Report](schemas/report.schema.json): update/question/done/blocked
- [Registry](schemas/registry.schema.json): non-secret routing configuration

Reject unknown fields/versions, malformed JSON, duplicate JSON keys, unknown bot
IDs, unapproved repos, and untrusted sender contexts. Never accept a report as a
task. Do not give arbitrary callback fields or embedded instructions authority.

## Session modes

- `existing`: verified session ID/link in the intended organization; no fallback
  unless `create_after_owner_approval` was selected and the owner approves.
- `new_persistent`: a fresh `message_session` automation with `auto_create`
  creates a session on its first trigger, then retains that fixed target.
- `new_per_task`: `start_session` creates an independent session for each task.

`if_missing` is application policy, not a Devin API field. A sleep is not a
missing session; v3 messages resume it. Access failures, ambiguous 404s, outages,
and timeouts never authorize replacement. Retrieve actual IDs from native tools
or documented API results and update the registry atomically.

## Response modes

| Mode | Routine reports | Safety exception |
|---|---|---|
| `none` | No update or done | Questions/blockers may still be sent; pause if no safe channel |
| `final` | Done | Questions/blockers |
| `progress` | Meaningful updates and done | Questions/blockers |

Setup requests always need a connection result or blocker. Answers inherit the
original task's mode. HTTP acceptance alone never authorizes a completion report.
`done` means the entire requested scope is complete; unresolved setup is blocked.

## Correlation and decisions

Each incoming operation has a unique `request_id`. Keep it stable on a retry.
A report's `request_id` is the original request it describes, not a newly
generated ID for every progress event. `bot_id` and `repo` preserve context.
Distinct questions get distinct `question_id` values.

An answer has its own request ID and `in_reply_to` equal to the pending question
ID. Verify the same bot, repo, and original session using durable question
state. Accept an answer only once.

For `new_per_task`, do not POST an answer to its `start_session` inbox: that
creates a different session. Use the v3 existing-session message API or a
separately approved inbox fixed to the original session. Store the approved
answer route in durable question state. If neither route exists, keep paused
and ask the owner to reply in the original Devin session. Body-level routing
fields cannot solve this. The offline `check_delivery` helper checks automation
deliveries; API answers need their own authenticated delivery context and the
same `check_answer` correlation check.

- `clarification`: a `select` answer must match an exact offered option.
- `permission`: only verified explicit owner `approve`/`deny` may resolve it.
- `platform_approval`: an answer cannot resolve the platform's approval gate;
  the owner must approve the actual Devin card.

For permission/platform approval, `default_if_no_answer` must be exactly
`Remain paused; do not perform the action.` Timeouts, missing responses, bot
guesses, and routine HTTP acknowledgments never count as approval.

## Persistence and retries

The host's registry/deduplication adapter must be a durable, owner-approved
store. Require an atomic request claim before side effects. Record canonical
request digest, status, bot, target, pending decision, and result correlation.
The same ID with different contents is a conflict, not a new task.

A claimed request left unresolved after a crash is **unknown**. Reconcile its
effects before retrying. Do not blindly replay an ambiguous POST or create a
second webhook/session after a timeout.

Read/update registry entries atomically and reject concurrent incompatible
changes. Do not store credentials or full secret-bearing transport bodies in
the registry, logs, or source control. Secret references alone belong there.

## Compatibility

The legacy return contract has eight required fields:
`kind`, `repo`, `session_url`, `pr`, `summary`, `details`, `options`,
`default_if_no_answer`.

Version 1 preserves them and requires correlation/decision extensions:
`protocol_version`, `request_id`, `bot_id`, `question_id`, `decision_type`.
Both adapters must explicitly enroll version 1 before sending these extensions.
Do not assume the deployed return relay accepts or interprets them.

Legacy transport may be used for baseline status reporting, but cannot be
claimed to implement this versioned routing/decision contract. Keep approval
decisions on the platform until correlation support is verified.

## Credential boundaries

1. Grok → Devin automation: `X-Webhook-Secret` unique to that inbox.
2. External Grok API client → Devin v3: modern service-user key/PAT and required
   organization permissions.
3. Devin → Grok relay: that relay's documented auth, currently bearer auth.

No credential values in requests, reports, metadata, examples, or repository
files. Newly minted inbox secrets need supported secure storage/exchange;
unsupported exchange is a blocker, not a reason to paste keys into chat.

Documented Devin repo references use `secret:repo:<owner>/<repo>:<NAME>`.
Other native scopes include `secret:org:`, `secret:personal:`, and
`secret:session:`. Verify the exact available reference through the host;
syntax alone does not prove availability. A registry reference such as
`adapter:grok:pua-review-inbox-secret` is an opaque alias for Grok's approved
adapter to map to its own secret store, not a documented Grok secret syntax.
Similarly, `adapter:devin:pua-review-return-key` must map through trusted local
configuration to a verified native reference or injected secret variable.
These aliases are not directly usable as `exec.env` bindings.
Do not assume either host can read the other host's secrets.

Only approved secrets and destinations from configuration may be resolved. The
message body cannot override them. No redirect-following credential transfers.
