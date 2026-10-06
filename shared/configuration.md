# Devin configuration reference

Reference checked against Devin docs and this organization's native automation
schemas on 2026-10-06. Always read live schemas before preparing a real change.
The JSON files in `examples/automation-*.json` are placeholder-based templates,
not executable production configurations.

## UI and native fields

The table covers the automation editor fields in this organization. Webhook
payload filters, shared scratchpad, and security profiles are editor-only here;
the native automation tool does not expose them.

| UI label | Native field | Options / default | Relay guidance |
|---|---|---|---|
| Name | `name` | 1–500 characters | Use a recognizable bot/relay label; metadata is the matching source of truth. |
| Active toggle | `enabled` | Boolean | Keep disabled until reviewed and ready for an owner-approved test. |
| Trigger: Webhook | `triggers[].event_type: "webhook:incoming"` | At most one per automation; takes no `conditions`. URL: `https://app.devin.ai/api/webhooks/automations/${org_id}/${automation_id}`. | Caller sends `X-Webhook-Secret`. |
| Secret | Webhook secret (not exposed in automation configuration) | Shown once when created; rotate icon in the editor. | Rotation breaks the caller until its stored secret is updated. |
| Payload filter | UI-only | Optional Python regex; case-sensitive `re.search` against JSON body for POST or query string for GET; empty matches all. | Not exposed by the native tool in this org and webhook triggers take no conditions. Set/change it in the webapp editor. For example, `"bot_id":\s*"pua-review"` pre-filters payloads but is not authentication. |
| Agent type | `actions[].type` | Start session = `start_session`; Message existing session = `message_session`; Auto triage = `triage_session`; Code scan = `start_code_scan` or `scan_new_commits`. | Relay destinations use only `start_session` / `message_session`. Start session creates one session per event (at most one action per automation) and supports `session.bypass_approval`, `session.tags`, `session.platform`. Message existing uses `target_devin_id` or `auto_create: true`. Triage uses `setup_prompt`, `slack_triage_config`; it is Slack-only (`slack:message` triggers), requires exactly one action, no webhook, and has no replies/notifications. `start_code_scan` uses `repo_name`/`repos`, `scan_type`, `profile_id`, and `code_scan_effort` (`lite` or `deep`); `scan_new_commits` uses `scan_id`. Code scans run as the code-scan service, not Devin prompt sessions. Recognize but leave triage and code-scan automations alone. |
| Destination session | `actions[].target_devin_id`; `actions[].auto_create` | `target_devin_id` is `devin-${session_id}`; `auto_create: true` creates a new persistent session and the server sets its target on first trigger. | The UI picker searches title or ID. Via tools, resolve a title with Devin session search and confirm with the owner when multiple sessions match. |
| Instructions | `actions[].prompt`; triage uses `setup_prompt` | Prompt text; event payload is appended automatically. Inline tokens: `@{owner}/{repo}`, `@playbook:{id}`, `@skills:{name}`, `!{macro}`, `${SECRET_NAME}`. | Include sender authentication, authorization, routing, and reporting policy. Uppercase `${SECRET_NAME}` tokens are Devin secret references; never replace them with values. |
| Agent mode | `session_settings.devin_mode`; `fallback_devin_mode` | `null` = Org default (Normal); available: `normal`, `fast`, `lite`, `ultra`, `fusion`. A research preview requires a stable `fallback_devin_mode`; suggest `normal`. | Ask before changing the mode; set a fallback whenever selecting a preview. |
| Run as | `run_as.type` | `creator` ("Creator (you)") or `organization` ("System User"); required on create. | Must match MCP installation scope. Creator is appropriate for personal credentials; organization identity requires compatible organization credentials. |
| MCPs | `tools.mcp_servers`; `tools.linear_enabled`; `tools.slack_channels`, `slack_dm_scope`, `teams_channels`, `teams_dm_scope` | `mcp_servers` uses marketplace slugs; empty means no MCP tools. Linear is a separate built-in checkbox. | Discover installed integrations and grant only those needed and compatible with run-as credentials. |
| Notifications | `notifications.email`; `notifications.slack` | Email: `{when: always|dispatch_failed|dispatch_succeeded, recipients}`; `recipients: null` means creator. Slack: `{channel_id, when}`. | Default relay choice: email on `dispatch_failed`. Notifications are dispatch status, not relay task results. |
| Shared scratchpad (Advanced) | UI-only | Toggle; long-term memory shared across all sessions run by the automation. | Not exposed by the native tool; set/change in the editor. Never store secrets there. |
| Network policy (Advanced) | `session_settings.net_policy.allow[]` | Entries are `{hostname}`, `{ipv4}`, or `{ipv6}`; wildcard hostnames such as `*.example.com` are allowed. Explicit `null` means unrestricted. | Start with `git-manager.devin.ai` plus `${relay_host}`. Explicit unrestricted access only on owner request; preserve existing entries on update. |
| Metadata | `metadata` | At most 16 pairs; keys ≤32 characters and values ≤128. An update with a null value deletes that key. | Use non-secret labels such as `relay_role`, `bot_id`, and `protocol_version`. |
| Limits (toggle): Spend limit per session | `limits.max_acu_limit` | UI is dollars; native value is ACUs, 1–1000; `null` means no limit. | Units differ: confirm the intended amount in the editor with the owner. |
| Limits (toggle): Rate limit | `limits.invocations.max_per_window`; `limits.invocations.window_seconds` | UI default 50 per 1 hour. UI windows 15 minutes / 1 hour / 6 hours / 12 hours / 24 hours / 7 days = 900 / 3600 / 21600 / 43200 / 86400 / 604800 seconds. API minimum 60 seconds; set both keys together. | Agree on both count and window with the owner; this is not message deduplication. |
| Enable queueing (toggle): Concurrent runs | `concurrency.max_concurrent_runs` | UI default 1; minimum 1. A run frees its slot when its session awaits instructions. | Keep at 1 unless the owner requests parallel work. |
| Enable queueing (toggle): Queue depth | `concurrency.max_queue_depth` | UI default no limit; minimum 0. Zero means never queue and extra events are dropped; requires `max_concurrent_runs`. | Choose deliberately; queued work can become stale while a session waits. |
| Security profile | Not settable from a Devin session | Owner selects it in the editor. | Ask the owner to select/change it in the webapp; do not try to override it through native tools. |

Reference repositories in prompts using the supported inline repo tokens.
Do not pass read-only `session.repos` or `session.playbook_id` as setup inputs.
The originating external sender still needs authentication/authorization;
run-as does not turn arbitrary payloads into owner approval.

## Network policy

The Git Manager starting policy plus the org's approved return-relay host:

```json
{
  "allow": [
    {"hostname": "git-manager.devin.ai"},
    {"hostname": "${relay_host}"}
  ]
}
```

`${relay_host}` is a placeholder; substitute the org's verified relay hostname
at setup time. Use exact hostname destinations; in the UI, add the hostname
itself, not a URL.
Do not disable restriction merely to make delivery work. If a security profile
governs networking, follow its approved policy instead of escaping it.
Preserve unrelated existing entries on updates.

These settings govern spawned sessions. A new automation does not guarantee
that an already-existing target session's policy changes. Use the target's
`get_network_allowlist` / `request_network_access` flow when necessary.
Grok's own API client needs separate outbound access on Grok's host.

## Metadata, limits, queue

Example labels: `relay_role=bootstrap|session`, `bot_id=pua-review`,
`protocol_version=1`. These are not routing expressions, secret values, or env
variables. Limits and queue values are summarized in the field reference above.

## Safe native management sequence

1. Invoke builtin `managing-automations` and discover exact tool parameters.
2. List/get existing resources.
3. Read schemas/integrations; resolve owner decisions.
4. Validate the exact create/update payload without approval.
5. Submit native create/update for approval.
6. Wait for its result; do not inspect/infer a pending approval's outcome.
7. Get the saved resource after approval and securely onboard the inbox secret.
8. Verify with an approved test; a manual run does not validate inbox auth.

## Update semantics

Updates use merge-patch. Omitted top-level parameters are unchanged. Within a
passed group, omitted keys keep their values and `null` clears a key. Lists
(including `triggers`, `actions`, and list-valued keys) replace wholesale, so
resend every list entry to preserve it. Re-check live schemas before a real
change. A platform approval card is not approved by a chat "yes" or relayed
API message.

## External API routing

Supported modern existing-session call:
`POST /v3/organizations/{org_id}/sessions/{devin_id}/messages`,
body `{"message":"..."}`. Requires `ManageOrgSessions`; suspended sessions
resume automatically. The session ID has the `devin-` prefix.

External creation: `POST /v3/organizations/{org_id}/sessions`. Read the current
create schema and permissions before implementing this external adapter.
Do not reuse v1 payload assumptions. Native Devin setup skills use native
resource tools, not guessed public API credentials.

## Secrets and installation

`list_secrets` lists references without values. Explicitly bind repo-scoped
references in a new `exec.env`; they are not auto-injected. An unknown reference
is a blocker. No automatic fallback from secret descriptions.

The new Devin inbox secret is minted on creation or webhook re-addition and
cannot be retrieved again. Securely capture it at that point using supported
storage. Do not remove/re-add a trigger casually: it can rotate credentials.

Devin accepts a plugin manifest in `.devin-plugin/plugin.json` with `skills/`
and optional supported assets. This draft does not define hooks/MCP servers.
Grok's provider directory is separate and needs its own host-approved installer.

## Official references

- [Automations](https://docs.devin.ai/product-guides/automations)
- [v3 existing-session messages](https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions-messages)
- [Authentication](https://docs.devin.ai/api-reference/authentication)
- [Webhook creation](https://docs.devin.ai/api-reference/v3/automations/post-organizations-automations)
- [Migration and session endpoints](https://docs.devin.ai/api-reference/getting-started/migration-guide)
- [Plugin layout](https://docs.devin.ai/cli/extensibility/plugins/overview)
