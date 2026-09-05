"""Deterministic public documents and human-readable rendering."""

from __future__ import annotations

import json
from typing import Any

import yaml

from .context import ResolvedHostContext
from .models import Appliance, Host

SCHEMA_VERSION = 1


def host_document(host: Host) -> dict[str, Any]:
    """Return one normalized declared host record in stable field order."""

    document: dict[str, Any] = {
        "host_id": host.host_id,
        "access": {"type": host.access.access_type},
        "operator": {"user": host.operator.user, "sudo": host.operator.sudo},
    }
    if host.access.host is not None:
        document["access"]["host"] = host.access.host
    if host.availability is not None:
        document["availability"] = {"mode": host.availability.mode}
    document["software"] = {
        "package_managers": {
            capability.capability_id: {} for capability in host.software.package_managers
        },
        "runtimes": {
            capability.capability_id: (
                {"managed_workloads_owner": capability.managed_workloads_owner}
                if capability.managed_workloads_owner is not None
                else {}
            )
            for capability in host.software.runtimes
        },
        "components": {capability.capability_id: {} for capability in host.software.components},
    }
    if host.management is not None and host.management.homelab_update is not None:
        document["management"] = {
            "homelab_update": {"mechanisms": list(host.management.homelab_update.mechanisms)}
        }
    if host.context.include:
        document["context"] = {"include": list(host.context.include)}
    return document


def appliance_document(appliance: Appliance) -> dict[str, Any]:
    """Return one normalized declared appliance record in stable field order."""

    access: dict[str, Any] = {"type": appliance.access.access_type}
    if appliance.access.host is not None:
        access["host"] = appliance.access.host
    return {
        "appliance_id": appliance.appliance_id,
        "kind": appliance.kind,
        "name": appliance.name,
        "access": access,
        "user": appliance.user,
    }


def hosts_document(hosts: tuple[Host, ...]) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "hosts": [host_document(host) for host in hosts]}


def host_contexts_document(contexts: tuple[ResolvedHostContext, ...]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "hosts": [
            {
                "configuration": host_document(context.host),
                "context": [
                    {"document_id": document.document_id, "content": document.content}
                    for document in context.documents
                ],
            }
            for context in contexts
        ],
    }


def resolved_host_document(host: Host) -> dict[str, Any]:
    """Preserve homelab-update's successful need-to-know resolver contract exactly."""

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ready",
        "exit_code": 0,
        "host_id": host.host_id,
        "access": host.access.access_type,
        "ssh_target": host.ssh_target,
    }


def resolved_appliance_document(appliance: Appliance) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ready",
        "exit_code": 0,
        "appliance_id": appliance.appliance_id,
        "kind": appliance.kind,
        "name": appliance.name,
        "access": appliance.access.access_type,
        "ssh_target": appliance.ssh_target,
    }


def fatal_document(error_code: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "fatal",
        "exit_code": 30,
        "error_code": error_code,
        "message": message,
    }


def render_json(document: object, mode: str) -> str:
    if mode == "full":
        return json.dumps(document, indent=2, ensure_ascii=False)
    return json.dumps(document, separators=(",", ":"), ensure_ascii=False)


def render_yaml(document: object) -> str:
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True).rstrip()


def render_context_human(contexts: tuple[ResolvedHostContext, ...]) -> str:
    sections: list[str] = []
    for context in contexts:
        sections.extend(
            [
                f"# {context.host.host_id}",
                "",
                "## Declared configuration",
                "",
                "```yaml",
                render_yaml(host_document(context.host)),
                "```",
            ]
        )
        for document in context.documents:
            sections.extend(
                [
                    "",
                    f"## Context: {document.document_id}",
                    "",
                    document.content.rstrip(),
                ]
            )
        sections.extend(["", "---", ""])
    if sections:
        sections = sections[:-3]
    return "\n".join(sections)
