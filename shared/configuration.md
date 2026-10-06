# Devin configuration reference

Reference checked against Devin docs and this organization's native automation
schemas on 2026-10-06. Always read live schemas before preparing a real change.
The JSON files in `examples/automation-*.json` are templates with synthetic
targets, not executable production configurations.

## UI and native fields

| UI | Native field | Purpose |
|---|---|---|
| Name | `name` | Human-readable label |
| Webhook trigger | `triggers[].event_type: webhook:incoming` | One inbox per automation; no body-driven routing conditions |
| Start new session | `actions[].type: start_session` | Fresh session for every trigger |
| Message existing session | `actions[].type: message_session`, `target_devin_id` | Fixed existing destination |
| New persistent destination | `message_session`, `auto_create: true` | Creates on first trigger; later messages reuse it |
| Instructions | `actions[].prompt` | Full context, repository, contract, and authorization rules |
| Run as | `run_as.type: creator` or `organization` | Identity and available credentials/integrations |
| MCPs | `tools.mcp_servers` | Only installed, needed, compatible integrations |
| Linear checkbox | `tools.linear_enabled` | Optional; not required by this relay |
| Agent mode | `session_settings.devin_mode` | Available stable mode or eligible preview |
| Network policy | `session_settings.net_policy.allow` | Outbound VM destinations |
| Notifications | `notifications` | Dispatch-failure email, distinct from relay results |
| Metadata | `metadata` | Non-secret labels |
| Spend cap | `limits.max_acu_limit` | Per spawned session |
| Rate limit | `limits.invocations` | Count and window |
| Queue | `concurrency` | Maximum in-flight runs and backlog |
| Child sessions | `actions[].session.bypass_approval` for `start_session` | Only child-session creation, not all approvals |

Run identity must match MCP installation scope. Creator is appropriate for
personal credentials; organization identity requires compatible organization
credentials. Discover live integrations; do not attach a connector requiring
unavailable interactive auth to an unattended run.

Reference repositories in prompts using the supported inline repo tokens.
Do not pass read-only `session.repos` or `session.playbook_id` as setup inputs.
The originating external sender still needs authentication/authorization;
run-as does not turn arbitrary payloads into owner approval.

## Network policy

This organization's current Git Manager starting policy plus return relay:

```json
{
  "allow": [
    {"hostname": "git-manager.devin.ai"},
    {"hostname": "api2.cursor.sh"}
  ]
}
```

Use exact hostname destinations; in the UI, add `api2.cursor.sh`, not a URL.
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
variables. Current limits: 16 pairs; keys 32 chars; values 128 chars.

Supported spend cap here: 1–1000 ACU. Invocation limit requires both a positive
`max_per_window` and `window_seconds >= 60`. Set budgets with the owner.
`max_concurrent_runs >= 1` serializes at 1; `max_queue_depth >= 0` requires that
cap. A queue can become stale while a session waits for approval, so size it
intentionally. These are not message deduplication mechanisms.

## Safe native management sequence

1. Invoke builtin `managing-automations` and discover exact tool parameters.
2. List/get existing resources.
3. Read schemas/integrations; resolve owner decisions.
4. Validate the exact create/update payload without approval.
5. Submit native create/update for approval.
6. Wait for its result; do not inspect/infer a pending approval's outcome.
7. Get the saved resource after approval and securely onboard the inbox secret.
8. Verify with an approved test; a manual run does not validate inbox auth.

Updates in this organization use merge-patch for config groups, while list
fields replace lists. Fetch and preserve complete action/trigger lists, and
re-check live update semantics. A platform approval card is not approved by a
chat "yes" or relayed API message.

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
