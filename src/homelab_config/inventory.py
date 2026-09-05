"""Load and validate canonical inventory membership and declared records."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .context import validate_context_graph, validate_context_id
from .errors import ConfigurationError, SelectionError
from .models import (
    Access,
    Appliance,
    Availability,
    Component,
    HomelabUpdateManagement,
    Host,
    HostContext,
    Inventory,
    Management,
    Operator,
    PackageManager,
    RuntimeCapability,
    Software,
)
from .yaml_input import load_yaml_file

SCHEMA_VERSION = 1
CONFIG_ROOT_ENV = "HOMELAB_CONFIG_ROOT"
SUPPORTED_ACCESS_TYPES = frozenset({"local", "ssh"})
SUPPORTED_SUDO_MODES = frozenset({"password_required", "passwordless"})
SUPPORTED_AVAILABILITY_MODES = frozenset({"on_demand", "always_on"})
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def resolve_config_root(config_root: str | Path | None = None) -> Path:
    """Resolve an explicit, environment, or editable-checkout configuration root."""

    candidate: str | Path
    if config_root is not None:
        candidate = config_root
    elif CONFIG_ROOT_ENV in os.environ:
        candidate = os.environ[CONFIG_ROOT_ENV]
        if not candidate:
            raise ConfigurationError(f"{CONFIG_ROOT_ENV} must not be empty")
    else:
        candidate = Path(__file__).resolve().parents[2]

    root = Path(candidate).expanduser().resolve()
    if not root.is_dir():
        raise ConfigurationError(f"configuration root is not a directory: {root}")
    if not (root / "inventory.yaml").is_file():
        raise ConfigurationError(f"configuration root does not contain inventory.yaml: {root}")
    return root


def load_inventory(config_root: str | Path | None = None) -> Inventory:
    """Load the complete repository configuration and context graph, failing closed."""

    root = resolve_config_root(config_root)
    index = _mapping(load_yaml_file(root / "inventory.yaml", "inventory index"), "inventory")
    _keys(index, {"schema_version", "hosts", "appliances"}, set(), "inventory")
    if index["schema_version"] != SCHEMA_VERSION:
        raise ConfigurationError(
            f"inventory schema_version must be {SCHEMA_VERSION}, got {index['schema_version']!r}"
        )

    host_ids = _id_list(index["hosts"], "inventory hosts")
    appliance_ids = _id_list(index["appliances"], "inventory appliances", allow_empty=True)
    _validate_index_files(root, "hosts", host_ids)
    _validate_index_files(root, "appliances", appliance_ids)

    hosts = tuple(_load_host(root / "hosts" / f"{host_id}.yaml", host_id) for host_id in host_ids)
    appliances = tuple(
        _load_appliance(root / "appliances" / f"{appliance_id}.yaml", appliance_id)
        for appliance_id in appliance_ids
    )
    validate_context_graph(root, hosts)
    return Inventory(hosts, appliances, str(root))


def select_hosts(inventory: Inventory, requested: Sequence[str] = ()) -> tuple[Host, ...]:
    """Select hosts using canonical IDs while preserving declared/requested order."""

    selections = tuple(requested) or ("all",)
    if "all" in selections:
        if selections != ("all",):
            raise SelectionError("'all' cannot be combined with explicit host IDs")
        return inventory.hosts
    if len(set(selections)) != len(selections):
        raise SelectionError("explicit host IDs must not be duplicated")
    return tuple(inventory.host(host_id) for host_id in selections)


def _load_host(path: Path, indexed_id: str) -> Host:
    fields = _mapping(load_yaml_file(path, f"host '{indexed_id}'"), f"host '{indexed_id}'")
    _keys(
        fields,
        {"host_id", "access", "operator", "software", "management"},
        {"availability", "context"},
        f"host '{indexed_id}'",
    )
    host_id = _canonical_id(fields["host_id"], f"host '{indexed_id}' internal ID")
    if host_id != indexed_id:
        raise ConfigurationError(
            f"host file/index ID '{indexed_id}' does not match internal ID '{host_id}'"
        )

    access = _parse_access(fields["access"], f"host '{host_id}'")
    operator = _parse_operator(fields["operator"], host_id)
    if access.access_type == "local" and operator.sudo != "password_required":
        raise ConfigurationError(f"local host '{host_id}' requires sudo=password_required")
    if access.access_type == "ssh" and operator.sudo != "passwordless":
        raise ConfigurationError(f"SSH host '{host_id}' requires sudo=passwordless")

    availability = (
        _parse_availability(fields["availability"], host_id) if "availability" in fields else None
    )
    software = _parse_software(fields["software"], host_id)
    management = _parse_management(fields["management"], host_id, software)
    context = _parse_context(fields.get("context"), host_id)
    return Host(host_id, access, operator, availability, software, management, context)


def _load_appliance(path: Path, indexed_id: str) -> Appliance:
    subject = f"appliance '{indexed_id}'"
    fields = _mapping(load_yaml_file(path, subject), subject)
    _keys(fields, {"appliance_id", "kind", "name", "access", "user"}, set(), subject)
    appliance_id = _canonical_id(fields["appliance_id"], f"{subject} internal ID")
    if appliance_id != indexed_id:
        raise ConfigurationError(
            f"appliance file/index ID '{indexed_id}' does not match internal ID '{appliance_id}'"
        )
    kind = _string(fields["kind"], f"{subject} kind")
    if kind != "home_assistant":
        raise ConfigurationError(f"{subject} has unsupported kind: {kind}")
    access = _parse_access(fields["access"], subject)
    if access.access_type != "ssh":
        raise ConfigurationError(f"{subject} requires SSH access in schema V1")
    return Appliance(
        appliance_id,
        kind,
        _string(fields["name"], f"{subject} name"),
        access,
        _string(fields["user"], f"{subject} user"),
    )


def _parse_access(value: object, subject: str) -> Access:
    fields = _mapping(value, f"{subject} access")
    access_type = _string(fields.get("type"), f"{subject} access type")
    if access_type not in SUPPORTED_ACCESS_TYPES:
        raise ConfigurationError(f"{subject} has unsupported access type: {access_type}")
    required = {"type", "host"} if access_type == "ssh" else {"type"}
    _keys(fields, required, set(), f"{subject} access")
    endpoint = _string(fields["host"], f"{subject} SSH endpoint") if access_type == "ssh" else None
    return Access(access_type, endpoint)


def _parse_operator(value: object, host_id: str) -> Operator:
    subject = f"host '{host_id}' operator"
    fields = _mapping(value, subject)
    _keys(fields, {"user", "sudo"}, set(), subject)
    sudo = _string(fields["sudo"], f"{subject} sudo")
    if sudo not in SUPPORTED_SUDO_MODES:
        raise ConfigurationError(f"host '{host_id}' has unsupported sudo mode: {sudo}")
    return Operator(_string(fields["user"], f"{subject} user"), sudo)


def _parse_availability(value: object, host_id: str) -> Availability:
    subject = f"host '{host_id}' availability"
    fields = _mapping(value, subject)
    _keys(fields, {"mode"}, set(), subject)
    mode = _string(fields["mode"], f"{subject} mode")
    if mode not in SUPPORTED_AVAILABILITY_MODES:
        raise ConfigurationError(f"host '{host_id}' has unsupported availability mode: {mode}")
    return Availability(mode)


def _parse_software(value: object, host_id: str) -> Software:
    subject = f"host '{host_id}' software"
    fields = _mapping(value, subject)
    _keys(fields, {"package_managers", "runtimes", "components"}, set(), subject)
    package_managers = _parse_package_managers(fields["package_managers"], host_id)
    runtimes = _parse_runtimes(fields["runtimes"], host_id)
    components = _parse_components(fields["components"], host_id)

    all_ids = [
        *(item.capability_id for item in package_managers),
        *(item.capability_id for item in runtimes),
        *(item.capability_id for item in components),
    ]
    if len(set(all_ids)) != len(all_ids):
        duplicate = next(item for item in all_ids if all_ids.count(item) > 1)
        raise ConfigurationError(
            f"host '{host_id}' has duplicate software capability ID: {duplicate}"
        )
    return Software(package_managers, runtimes, components)


def _parse_package_managers(value: object, host_id: str) -> tuple[PackageManager, ...]:
    fields = _mapping(value, f"host '{host_id}' package managers")
    result: list[PackageManager] = []
    for raw_id, metadata in fields.items():
        capability_id = _canonical_id(raw_id, f"host '{host_id}' package manager ID")
        metadata_fields = _mapping(
            metadata, f"host '{host_id}' package manager '{capability_id}' metadata"
        )
        _keys(metadata_fields, set(), set(), f"package manager '{capability_id}' metadata")
        result.append(PackageManager(capability_id))
    return tuple(result)


def _parse_components(value: object, host_id: str) -> tuple[Component, ...]:
    fields = _mapping(value, f"host '{host_id}' components")
    result: list[Component] = []
    for raw_id, metadata in fields.items():
        capability_id = _canonical_id(raw_id, f"host '{host_id}' component ID")
        metadata_fields = _mapping(
            metadata, f"host '{host_id}' component '{capability_id}' metadata"
        )
        _keys(metadata_fields, set(), set(), f"component '{capability_id}' metadata")
        result.append(Component(capability_id))
    return tuple(result)


def _parse_runtimes(value: object, host_id: str) -> tuple[RuntimeCapability, ...]:
    fields = _mapping(value, f"host '{host_id}' runtimes")
    result: list[RuntimeCapability] = []
    for raw_id, metadata in fields.items():
        capability_id = _canonical_id(raw_id, f"host '{host_id}' runtime ID")
        subject = f"host '{host_id}' runtime '{capability_id}' metadata"
        metadata_fields = _mapping(metadata, subject)
        _keys(metadata_fields, set(), {"workload_desired_state_owner"}, subject)
        owner = (
            _string(metadata_fields["workload_desired_state_owner"], f"{subject} owner")
            if "workload_desired_state_owner" in metadata_fields
            else None
        )
        if capability_id == "docker" and owner != "homelab-docker":
            raise ConfigurationError(
                f"host '{host_id}' Docker runtime must declare "
                "workload_desired_state_owner=homelab-docker"
            )
        result.append(RuntimeCapability(capability_id, owner))
    return tuple(result)


def _parse_management(value: object, host_id: str, software: Software) -> Management:
    subject = f"host '{host_id}' management"
    fields = _mapping(value, subject)
    _keys(fields, {"homelab_update"}, set(), subject)
    update_subject = f"host '{host_id}' homelab_update management"
    update = _mapping(fields["homelab_update"], update_subject)
    _keys(update, {"mechanisms"}, set(), update_subject)
    mechanisms = _string_list(update["mechanisms"], f"{update_subject} mechanisms")
    if not mechanisms:
        raise ConfigurationError(f"{update_subject} mechanisms must not be empty")
    if len(set(mechanisms)) != len(mechanisms):
        raise ConfigurationError(f"host '{host_id}' has duplicate homelab_update mechanisms")
    declared = {
        *(item.capability_id for item in software.package_managers),
        *(item.capability_id for item in software.components),
    }
    undeclared = [mechanism for mechanism in mechanisms if mechanism not in declared]
    if undeclared:
        raise ConfigurationError(
            f"host '{host_id}' homelab_update mechanism '{undeclared[0]}' "
            "is not a declared package manager or component"
        )
    return Management(HomelabUpdateManagement(mechanisms))


def _parse_context(value: object | None, host_id: str) -> HostContext:
    if value is None:
        return HostContext()
    subject = f"host '{host_id}' context"
    fields = _mapping(value, subject)
    _keys(fields, {"include"}, set(), subject)
    includes = _string_list(fields["include"], f"{subject} include")
    if len(set(includes)) != len(includes):
        raise ConfigurationError(f"host '{host_id}' has duplicate context includes")
    for document_id in includes:
        validate_context_id(document_id, subject=f"host '{host_id}' context include")
    return HostContext(includes)


def _validate_index_files(root: Path, collection: str, identifiers: tuple[str, ...]) -> None:
    directory = root / collection
    expected = {directory / f"{identifier}.yaml" for identifier in identifiers}
    missing = [path for path in expected if not path.is_file()]
    if missing:
        first = min(missing, key=lambda path: path.name)
        raise ConfigurationError(f"indexed {collection[:-1]} file is missing: {first}")

    actual: set[Path] = set()
    if directory.is_dir():
        actual.update(directory.rglob("*.yaml"))
        actual.update(directory.rglob("*.yml"))
    extras = actual - expected
    if extras:
        first = min(extras, key=lambda path: str(path))
        raise ConfigurationError(f"unindexed {collection[:-1]} YAML exists: {first}")


def _mapping(value: object, subject: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{subject} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ConfigurationError(f"{subject} mapping keys must be strings")
    return value


def _keys(
    fields: Mapping[str, Any],
    required: set[str],
    optional: set[str],
    subject: str,
) -> None:
    missing = required - fields.keys()
    if missing:
        raise ConfigurationError(f"{subject} is missing required field: {min(missing)}")
    unexpected = fields.keys() - required - optional
    if unexpected:
        raise ConfigurationError(f"{subject} has unexpected field: {min(unexpected)}")


def _string(value: object, subject: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ConfigurationError(f"{subject} must be a non-empty trimmed string")
    return value


def _canonical_id(value: object, subject: str) -> str:
    identifier = _string(value, subject)
    if _ID.fullmatch(identifier) is None:
        raise ConfigurationError(f"{subject} is not a valid canonical ID: {identifier}")
    return identifier


def _string_list(value: object, subject: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ConfigurationError(f"{subject} must be a list")
    return tuple(_string(item, f"{subject} item") for item in value)


def _id_list(value: object, subject: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    identifiers = tuple(_canonical_id(item, f"{subject} item") for item in _list(value, subject))
    if not identifiers and not allow_empty:
        raise ConfigurationError(f"{subject} must not be empty")
    if len(set(identifiers)) != len(identifiers):
        raise ConfigurationError(f"{subject} contains duplicate IDs")
    return identifiers


def _list(value: object, subject: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigurationError(f"{subject} must be a list")
    return value
