# Homelab Config

This repository is the canonical, read-only registry for stable homelab identity, access,
capabilities, selected management scope, and semantic context. It is not a desired-state database.

## Boundaries

- Never add secrets, credentials, tokens, private keys, or secret-derived values.
- Never add runtime observations such as versions, packages, update candidates, running containers,
  service state, disk usage, or audit results.
- Never add Docker stack membership or Compose definitions. `homelab-docker` exclusively owns
  managed Docker desired state under `hosts/<canonical-host-id>/<stack>/compose.yaml`.
- Do not infer canonical IDs from SSH aliases, access endpoints, DNS, runtime hostnames, or local
  hostnames. Only `inventory.yaml` defines canonical membership and order.
- New structured fields must be stable facts needed by multiple consumers or a clearly justified
  central management contract. Keep specialized desired state in its domain repository.
- Put nuanced semantic facts and exception reasoning in context Markdown when forcing them into
  YAML would create a weak schema.
- Do not duplicate structured YAML facts in context prose without a strong reason.

## Implementation rules

- Keep the CLI and library strictly read-only: no SSH, sudo, package-manager calls, runtime probes,
  sibling-repository changes, or configuration writes.
- Use immutable typed models internally and safe YAML loading that rejects duplicate keys.
- Fail closed on missing files, unindexed YAML, contradictions, unknown canonical IDs, and invalid
  context references. Never guess around incomplete configuration.
- Preserve canonical index order, explicit selection order, deterministic field order, and clean
  JSON stdout.
- Preserve `schema_version = 1` and the exact successful `resolve-host` compatibility document
  unless a deliberate versioned contract change is requested.
- Context output must remain bounded to the selected hosts: mandatory host document first, followed
  by explicit includes in declared order.
- Keep parsing, immutable models, selection, context resolution, and rendering independently
  testable. Do not turn this small registry into a framework or add a TUI.

## Validation

From the repository root, run:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```

