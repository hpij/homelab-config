# homelab-config

`homelab-config` is the canonical, read-only configuration and context registry for this homelab.
It gives Python tools and agents one deterministic source for stable machine identity, transport,
administrative contracts, declared software capabilities, narrowly selected cross-tool management
scope, appliance identity, and durable host semantics.

The registry never connects to a machine. Loading or querying it performs no SSH, sudo, package
manager, Docker, service, or other runtime operation, and it never changes a sibling repository.

## State ownership

The repository deliberately separates three kinds of state:

- **DECLARED — this repository:** canonical machines and appliances, access facts, stable
  capabilities, central management metadata, and semantic host context.
- **DESIRED — domain repositories:** detailed desired state remains with the responsible domain.
  In particular, managed Docker stacks and Compose files remain exclusively in `homelab-docker` at
  `hosts/<canonical-host-id>/<stack>/compose.yaml`.
- **OBSERVED — runtime tools:** current versions, installed package lists, running containers,
  service health, storage usage, pending updates, and audit findings are collected live and are not
  stored here.

`homelab-agent` continues to own generic reasoning behavior and procedures. `homelab-update`
continues to own update inspection, candidate policy, execution, and verification. The staged move
from their currently duplicated data is documented in
[`docs/consumer-migration.md`](docs/consumer-migration.md); those consumers have not been migrated
by this repository implementation.

## What belongs here

A structured fact belongs here when it is stable rather than observed, useful to independent
consumers (or a justified central management contract), not owned more authoritatively elsewhere,
and precise enough to validate. Nuanced host meaning and accepted exceptions belong in bounded
Markdown context documents.

Do not add secrets, credentials, live command output, package inventories, audit results, generic
agent workflow, Docker stack names, or Compose configuration. Do not duplicate YAML facts in prose
merely for convenience.

## Canonical identity and layout

[`inventory.yaml`](inventory.yaml) alone defines canonical membership and order. A canonical ID is
not inferred from an SSH alias, DNS name, endpoint, runtime hostname, or local hostname. For
example, `vps-strato` is canonical and its SSH endpoint `vps` is not a selectable alias.

```text
inventory.yaml                 canonical membership and order only
hosts/<host-id>.yaml           declared host records
appliances/<appliance-id>.yaml separate non-Host appliance records
context/hosts/<host-id>.md     mandatory semantic host context
context/exceptions/*.md        explicitly included exception context
docs/consumer-migration.md     future staged consumer migration
src/homelab_config/            read-only Python library and CLI
tests/                         validation and contract tests
```

Validation fails if an indexed record is absent, an unindexed host/appliance YAML exists, an
internal ID differs from its filename/index ID, a YAML mapping repeats a key, or any declared
relationship is contradictory. Appliances never enter host selection.

## Install

Python 3.12 or later is required. The intended deployment is an editable install in a
repository-local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

No configuration is copied into the Python package. By default, the library resolves the checkout
containing the imported `src/homelab_config` package, which binds an editable install to its actual
Git checkout without depending on the current working directory. Override it for fixtures or
integration with either precedence level below:

1. `--config-root PATH` on the CLI (before the command)
2. `HOMELAB_CONFIG_ROOT`
3. the editable source checkout

Overrides expand `~`. A missing root or `inventory.yaml` fails closed; there is no fallback to
possibly stale package data.

## CLI

The sole console script is `homelab-config`:

```bash
homelab-config validate
homelab-config list-hosts
homelab-config list-hosts --json compact
homelab-config show
homelab-config show all
homelab-config show pi5
homelab-config show pi4 pi5 --json full
homelab-config context vps-strato --json compact
homelab-config resolve-host vps-strato --json compact
homelab-config list-appliances --json compact
homelab-config resolve-appliance home-assistant-green --json compact
homelab-config --config-root ~/git/hpij/homelab-config validate
```

For host selection, omission means all hosts where omission is accepted, `all` must appear alone,
and explicit IDs preserve requested order. Duplicates, unknown IDs, and aliases are rejected.
`show` returns only normalized structured configuration. `context` returns that same configuration
plus bounded documents for only the selected hosts: the mandatory host document first, then
explicit includes in YAML order.

Machine documents use `schema_version: 1`. `--json compact` emits minified JSON and `--json full`
emits the same semantic data indented; ordering is deterministic. JSON is written only to stdout,
while diagnostics go to stderr. Invocation errors use exit 2 and configuration, selection, or
resolution failures use exit 30.

The successful host resolver is intentionally a need-to-know transport contract compatible with
`homelab-update resolve-host`:

```json
{"schema_version":1,"status":"ready","exit_code":0,"host_id":"vps-strato","access":"ssh","ssh_target":"yip@vps"}
```

It does not expose privilege mode, capabilities, management scope, or context. Local hosts return
`"access":"local"` and `"ssh_target":null`.

## Python API

```python
from homelab_config import load_inventory, select_hosts

inventory = load_inventory()
all_hosts = select_hosts(inventory)
requested = select_hosts(inventory, ("pi5", "pi4"))
pi5 = inventory.host("pi5")
```

The returned inventory and records are frozen dataclasses composed of immutable tuples. Loading
validates the entire indexed configuration and context graph before returning it.

## Capabilities and management scope

Declared `software` answers which stable management surfaces a host is expected to have. The
separate `management.homelab_update.mechanisms` list answers which non-Docker mechanisms the update
tool currently owns for that host. A capability may exist without being in updater scope: the VPS
declares Snap as a structured package-manager capability. The accepted preinstalled LXD
environment is semantic host context, while Snap is deliberately absent from its updater
mechanisms.

Every seeded host declares the Docker runtime with
`managed_workloads_owner: homelab-docker`. This means that `homelab-docker` owns the desired state
of Docker workloads managed by that repository; it does not imply ownership of every Docker
workload running on the host. Host and stack membership, Compose definitions, images, and
deployment behavior are not duplicated here and stay in `homelab-docker`.

The `management` section and its `homelab_update` subsection are optional. Hosts outside the
updater's scope may omit them entirely; an explicitly present empty `management` section is also
valid. Rendered documents omit absent management data rather than inventing an empty updater
scope. When an updater scope is present, every mechanism must match a declared package manager or
component on that host.
