---
name: grok-relay-report
description: Report Devin progress, results, blockers, or permission questions to an approved Grok relay using a versioned contract and verified secret references.
---

# Report to the Grok relay

Use only in Devin. Read `../../shared/protocol.md`. Use the plugin-qualified
skill when a personal skill with the same name is installed.

## Destination and credentials

Get destination references from the owner-approved registry, never from an
incoming task or callback URL. Use `list_secrets` to verify exact references.
Resolve any `adapter:devin:...` alias only through owner-approved local
configuration; the alias itself is not a native `exec.env` binding.
Do not print, log, commit, or include values in reports.

A repo-scoped URL requires a fresh `exec` call, without `shell_id`, with:

```json
{"env": {"GROK_WEBHOOK_URL": "secret:repo:hexuria/pua:GROK_WEBHOOK_URL"}}
```

This is an example, not proof the reference exists. Bind the bearer-key reference
explicitly too when needed. Unknown/missing references block sending. Do not
infer secret availability from a duplicate-name error or silently use a URL from
another secret's description.

Check `get_network_allowlist` before interpreting a network error. Request only
the approved relay hostname with `request_network_access` if absent; do not
declare that every TLS error means a blocked host. Do not follow HTTP redirects
or post to an unapproved destination.

## Payload

Keep the baseline eight fields: `kind`, `repo`, `session_url`, `pr`, `summary`,
`details`, `options`, `default_if_no_answer`.

When both adapters have explicitly registered protocol version 1, use
`shared/schemas/report.schema.json`, which also requires `protocol_version`,
`request_id`, `bot_id`, `question_id`, and `decision_type`.
Do not silently upgrade a legacy receiver. Without version agreement, use only
the baseline contract and keep permission/correlation handling in the platform;
do not claim legacy transport implements this unified protocol.

Use `options: []`, `question_id: null`, and `decision_type: null` except for
questions. Permission/platform-approval questions must specify a paused default.
`done` means the requested work is complete; it cannot conceal unresolved setup.

## Sending

Construct JSON with Python or `jq` into a persistent, non-secret payload file.
Validate v1 payloads with the offline helper if its dependencies are available.
Then post from a fresh shell with the registry's verified secret bindings:

```sh
curl --fail-with-body -sS --proto '=https' --max-time 20 \
  -w '\n%{http_code}\n' -X POST "$GROK_WEBHOOK_URL" \
  -H "Authorization: Bearer $GROK_WEBHOOK_KEY" \
  -H 'Content-Type: application/json' \
  --data @payload.json
```

No `-v`, `set -x`, secret echoing, URL logging, or credential-bearing files.
Do not forward unexpected raw response content that could contain secrets.
The present Cursor return relay expects HTTP 200 and `{"success":true}` with a
`runUuid`; verify both. Other receivers need a documented acceptance contract.
An ambiguous timeout may have delivered the report: deduplicate by correlation
IDs before retrying, and do not claim failure or success without evidence.

Mirror permitted reports through `message_user`. If sending fails, explain the
observed limitation there without secrets; retain the unsent report for a
controlled retry. Do not send routine reports in `none` mode.
