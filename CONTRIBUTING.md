# Contributing

Development setup and offline checks for this repository. These checks never
send HTTP requests, modify a session, or create automation resources. Live
integration testing must use owner-approved test destinations, with evidence
of both transport acceptance and the resulting session behavior.

## Setup

Python 3.10+ is required. Runtime helpers use `jsonschema`; checks also use
PyYAML. Install development dependencies from `requirements-dev.txt`:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

## Offline checks

```sh
python3 -m unittest discover -s tests -v
python3 scripts/relay_contract.py request examples/connect-existing.json
python3 scripts/relay_contract.py report examples/permission-question.json
python3 scripts/relay_contract.py registry examples/registry.json
python3 -m compileall -q scripts tests
python3 -m flake8 scripts tests --max-line-length=100
python3 -m mypy scripts --ignore-missing-imports
```

See `VERIFICATION.md` for the current pass/fail status and what remains
unverified.

## Conventions

- Identifiers in docs, examples, and tests are synthetic
  (`devin-00000000000000000000000000000001`, `org-example`,
  `relay.example.com`). Never commit real session IDs, org/automation IDs,
  internal hostnames, or credential values — a repo-scanning test enforces
  this for session IDs.
- Secret *references* (`secret:repo:...`, `adapter:...` aliases) and
  environment variable names may appear where needed; values never.
- Example automation JSON stays `enabled: false` with `EXAMPLE ONLY` prompts.
