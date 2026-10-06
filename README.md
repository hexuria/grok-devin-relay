# Grok ↔ Devin relay

**Early draft under review.** No live webhooks were created, no plugin was
installed, and no remote transport was tested. Grok's actual runtime and
webhook-management APIs need confirmation.

One repository holds a shared contract and two provider adapters. Installing
the Devin plugin does not install or activate Grok's adapter.

## The important routing rule

A Devin automation webhook has a configured action. Putting a session link in
its POST body does **not** retarget that action.

- **Bootstrap webhook:** messages a control-plane session that prepares other
  webhooks. Creation is asynchronous and may require platform approval.
- **Dedicated webhook:** configured for one existing/persistent session, or
  configured to start a new session for every incoming task.
- **Dynamic routing:** an external Grok router/registry or the official v3 API
  chooses the destination. It is not built into a body-level `session_id`.

For the example session
`https://app.devin.ai/sessions/1cc5cef5b0f04938a9f49ce7cd0d9fd0`,
send a *connect request* to bootstrap, then use the returned dedicated
destination after approval. Do not expect a task sent to bootstrap to
automatically execute in that session.

## Skills and installation boundary

| Stage | Devin | Grok |
|---|---|---|
| Install | `skills/relay-install/SKILL.md` | Grok adapter's install stage |
| First connection | `skills/relay-bootstrap-devin/SKILL.md` | Grok adapter's bootstrap stage |
| Choose session / create webhook | `skills/relay-connect-session/SKILL.md` | Grok adapter's registry/routing stage |
| Send tasks and answers | `skills/relay-message/SKILL.md` | Grok adapter's message stage |
| Report results / ask permission | `skills/grok-relay-report/SKILL.md` | Grok adapter's receive/answer stage |

Devin's `.devin-plugin/plugin.json` loads only the root `skills/` directory.
The Grok entry point is `providers/grok/SKILL.md`, outside that directory.
Grok must confirm its installer and supported API before enabling its adapter.

To install on Devin, inspect this repository, then ask Devin to install it as a
plugin using the native `manage_plugin` workflow, or use Customize → Plugins →
From repository. Choose personal or account scope explicitly. Do not install
this draft as if it were a reviewed release.

The existing personal `grok-relay-report` skill may remain installed. Use the
new plugin-qualified name to avoid ambiguous invocation. Remove or migrate the
old skill only after testing and with the owner's approval.

## Shared contract

- [Protocol and safety](shared/protocol.md)
- [Automation configuration](shared/configuration.md)
- `shared/schemas/`: versioned request, report, and registry JSON Schemas
- `examples/`: synthetic credentials-free fixtures and automation templates
- `scripts/relay_contract.py`: offline validation/normalization helpers only

There is **no production router, registry service, credential exchange, or
webhook server** in this draft. The skills guide the host's supported tools.
Do not mistake the offline Python helpers for an installed integration.

Response modes: `none`, `final`, and `progress`. Blockers/questions are safety
exceptions to silence. Permission requests always pause; a platform approval
card must be approved on the platform, not just answered in chat.

For new-per-task bots, answers must use a separate original-session route,
not the webhook that starts new tasks. See the protocol's correlation rules.

## Offline checks

Python 3.10+ is required. Runtime helpers use `jsonschema`; checks also use
PyYAML. Install development dependencies from `requirements-dev.txt` if needed:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
python3 scripts/relay_contract.py request examples/connect-existing.json
python3 scripts/relay_contract.py report examples/permission-question.json
python3 scripts/relay_contract.py registry examples/registry.json
python3 -m compileall -q scripts tests
python3 -m flake8 scripts tests --max-line-length=100
python3 -m mypy scripts --ignore-missing-imports
```

These checks do not send HTTP requests, modify a session, or create automation
resources. Live integration testing must use owner-approved test destinations,
with evidence of both transport acceptance and the resulting session behavior.

## What Grok needs to review

1. Runtime name and skill installation format.
2. Official tools/docs for creating the return webhook and authenticating it.
3. Secret storage/reference format and a secure exchange mechanism for newly
   minted Devin inbox secrets.
4. Durable registry and deduplication storage, including atomic writes.
5. API permissions and network egress from Grok's own host.
6. Support for protocol version 1 and correlated question/answer messages.

Share documentation and redacted examples, never real keys or webhook secrets.
Both adapters should use the same schemas rather than maintaining divergent
field lists.
