# Draft verification — 2026-10-06

Offline checks run on this draft's contents. Results were reproduced
independently in a fresh clone on the same date.

## Passed locally

- `python3 -m unittest discover -s tests -v`: 50 tests passed.
- `python3 -m flake8 scripts tests --max-line-length=100`: passed.
- `python3 -m compileall -q scripts tests`: passed.
- `python3 -m mypy scripts --ignore-missing-imports`: passed; no issues in
  2 source files.
- Request, permission-question report, and registry CLI examples: passed.
- All JSON fixtures parse; shared request/report/registry examples validate.
- Plugin manifest, provider boundary, skill frontmatter, and local document
  links were checked.
- Negative cases cover unapproved routing overrides, wrong session/organization,
  invalid links, unknown fields/versions, mismatched decisions, stale questions,
  native approval gates, duplicate JSON keys, and unsafe permission defaults.
- A new-per-task inbox rejects answers; the original-session answer route is
  explicitly required.

The schemas use JSON Schema Draft 7. Final checks ran in an isolated Python
3.10.20 environment with `jsonschema 4.23.0`, `PyYAML 6.0.2`, `flake8 7.3.0`,
and `mypy 1.15.0`, satisfying the declared development dependencies.

## Not verified

- No live HTTP delivery, webhook creation, secret exchange, plugin installation,
  or durable registry integration was exercised.
- Example automation templates are disabled and use synthetic IDs. They have
  not been submitted to native validation as real production configurations.
- Grok's runtime, installer, APIs, and storage capabilities remain unconfirmed.
- The repository was empty at publication; no README, AGENTS, hooks, or
  contribution rules existed to reconcile against.
- No accessible Grok bearer credential was listed during the latest secret
  check, so a Grok relay status could not be posted.

Do not treat these offline checks as proof of an installed or functioning relay.
