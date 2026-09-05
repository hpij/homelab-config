# Consumer migration

This document records the intended staged removal of configuration duplicated by current
consumers. It does not prescribe untested implementation details, and none of these migrations are
part of the initial `homelab-config` implementation.

## Phase 1: homelab-agent

- Switch both resolver integrations from `homelab-update resolve-host` to the compatible
  `homelab-config resolve-host` command.
- Replace direct host-fact discovery with one bounded `homelab-config context` request for the
  selected host scope.
- Remove host and exception facts that have been migrated to this registry.
- Retain generic agent reasoning, behavior, procedural policy, runbooks, and skills in the agent
  repository.

## Phase 2: homelab-update

- Stop owning canonical host identity and transport; consume structured host configuration from
  `homelab-config`.
- Derive and preserve the existing non-Docker mechanism scope from central
  `management.homelab_update` metadata.
- Remove the updater's packaged duplicate `hosts.yaml`.
- Migrate Home Assistant Green identity from the updater's packaged appliance configuration.
- Keep all update inspection, candidate authority, execution policy, safety, and verification in
  `homelab-update`, preserving those contracts exactly.

## Phase 3: homelab-docker

- Keep `hosts/<host-id>/<stack>/compose.yaml` as the sole managed Docker desired-state authority.
- Eliminate duplicated Ansible transport identity, or validate it against `homelab-config` during a
  transition.
- Consider a small generated or dynamic Ansible inventory adapter only after the direct consumers
  are migrated and tested.
- Never move stack membership or Compose definitions into `homelab-config`.

## Phase 4: future homelab-audit

- Do not create a private host inventory.
- Derive applicable collectors from declared central software capabilities.
- Support `all`, one host, and an explicit ordered host subset.
- Remain strictly read-only; observations and findings stay outside this registry.

