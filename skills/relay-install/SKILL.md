---
name: relay-install
description: Install and verify the Devin side of the shared Grok-to-Devin relay without activating the Grok adapter or changing live routing.
---

# Install the relay

Use only in Devin. Read `../../shared/protocol.md` and
`../../shared/configuration.md` from this skill directory.

1. Inspect the source and manifest before installation. Check the repository's
   own contribution rules when working on its contents.
2. Ask for personal versus account scope if not already chosen. Use the native
   `manage_plugin` approval flow; installing a plugin does not authorize
   automation creation, broader networking, or secret rescoping.
3. Keep only Devin skills in the root `skills/`. Grok's adapter lives in
   `providers/grok/`; do not install a foreign provider manifest into Devin or
   imply Grok will understand Devin's tools.
4. Verify the intended secret references with `list_secrets`, without reading
   or printing values. Select the return URL and key references with the owner.
   Repo-scoped secrets require explicit `exec.env` bindings in a fresh shell.
   Unknown references block reporting; a duplicate-name UI error is not proof
   of availability or scope.
5. Discover automation schemas and available integrations with native tools.
   Verify the run identity can use the chosen secrets and MCPs. Do not request
   an API key for native Devin management tools.
6. The installer prepares the host; it does not create or retarget webhooks.
   Next invoke `relay-bootstrap-devin` for the first connection.

If an older personal `grok-relay-report` exists, use the plugin-qualified new
skill. Do not delete the old skill until the owner approves the migration.

Installing into a managed plugin applies to future sessions as described by the
native tool. Do not claim the current session has reloaded all new skills.
