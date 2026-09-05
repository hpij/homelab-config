from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from homelab_config import load_inventory, select_hosts
from homelab_config.context import load_host_context
from homelab_config.errors import ConfigurationError, SelectionError
from homelab_config.models import Access, Appliance, Host


def _read_host(config_root: Path, host_id: str) -> dict[str, object]:
    return yaml.safe_load((config_root / "hosts" / f"{host_id}.yaml").read_text())


def _write_host(config_root: Path, host_id: str, document: dict[str, object]) -> None:
    (config_root / "hosts" / f"{host_id}.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )


def test_seeded_inventory_has_exact_canonical_order_and_appliance(config_root: Path) -> None:
    inventory = load_inventory(config_root)

    assert inventory.host_ids == ("yip-i3wm", "pi4", "pi5", "vps-strato")
    assert inventory.appliance_ids == ("home-assistant-green",)
    assert inventory.appliance("home-assistant-green") == Appliance(
        "home-assistant-green",
        "home_assistant",
        "Home Assistant Green",
        Access("ssh", "homeassistant.local"),
        "hassio",
    )
    assert inventory.appliance("home-assistant-green").ssh_target == ("hassio@homeassistant.local")


def test_seeded_host_capabilities_management_scope_and_availability(config_root: Path) -> None:
    inventory = load_inventory(config_root)

    expected = {
        "yip-i3wm": (
            ("apt", "flatpak", "snap"),
            ("docker", "libvirt"),
            ("hermes",),
            ("apt", "flatpak", "snap", "hermes"),
            "on_demand",
        ),
        "pi4": (("apt",), ("docker",), ("pihole",), ("apt", "pihole"), None),
        "pi5": (("apt",), ("docker",), (), ("apt",), None),
        "vps-strato": (
            ("apt", "snap"),
            ("docker",),
            ("nextcloud_aio",),
            ("apt", "nextcloud_aio"),
            None,
        ),
    }
    actual = {
        host.host_id: (
            tuple(item.capability_id for item in host.software.package_managers),
            tuple(item.capability_id for item in host.software.runtimes),
            tuple(item.capability_id for item in host.software.components),
            host.management.homelab_update.mechanisms,
            host.availability.mode if host.availability else None,
        )
        for host in inventory.hosts
    }
    assert actual == expected


def test_local_and_ssh_hosts_parse_without_inferred_identity(config_root: Path) -> None:
    inventory = load_inventory(config_root)
    local = inventory.host("yip-i3wm")
    remote = inventory.host("vps-strato")

    assert isinstance(local, Host)
    assert local.access == Access("local")
    assert local.ssh_target is None
    assert local.operator.user == "yip"
    assert local.operator.sudo == "password_required"
    assert remote.access == Access("ssh", "vps")
    assert remote.ssh_target == "yip@vps"


def test_inventory_models_are_frozen(config_root: Path) -> None:
    host = load_inventory(config_root).host("pi5")
    with pytest.raises(FrozenInstanceError):
        host.host_id = "other"  # type: ignore[misc]


def test_selection_all_single_subset_and_omission(config_root: Path) -> None:
    inventory = load_inventory(config_root)

    assert tuple(host.host_id for host in select_hosts(inventory)) == inventory.host_ids
    assert tuple(host.host_id for host in select_hosts(inventory, ("all",))) == inventory.host_ids
    assert tuple(host.host_id for host in select_hosts(inventory, ("pi5",))) == ("pi5",)
    assert tuple(host.host_id for host in select_hosts(inventory, ("pi5", "pi4"))) == (
        "pi5",
        "pi4",
    )


@pytest.mark.parametrize(
    ("requested", "message"),
    [
        (("pi4", "pi4"), "must not be duplicated"),
        (("all", "pi4"), "cannot be combined"),
        (("unknown",), "unknown canonical host ID"),
        (("vps",), "unknown canonical host ID"),
    ],
)
def test_selection_rejects_duplicates_mixed_all_unknowns_and_aliases(
    config_root: Path, requested: tuple[str, ...], message: str
) -> None:
    with pytest.raises(SelectionError, match=message):
        select_hosts(load_inventory(config_root), requested)


def test_duplicate_yaml_key_is_rejected(config_root: Path) -> None:
    path = config_root / "hosts" / "pi5.yaml"
    path.write_text(path.read_text().replace("host_id: pi5", "host_id: pi5\nhost_id: other"))

    with pytest.raises(ConfigurationError, match="duplicate key 'host_id'"):
        load_inventory(config_root)


def test_duplicate_inventory_ids_are_rejected(config_root: Path) -> None:
    path = config_root / "inventory.yaml"
    path.write_text(path.read_text().replace("  - pi5\n", "  - pi5\n  - pi5\n"))
    with pytest.raises(ConfigurationError, match="inventory hosts contains duplicate IDs"):
        load_inventory(config_root)


def test_missing_indexed_host_file_is_rejected(config_root: Path) -> None:
    (config_root / "hosts" / "pi5.yaml").unlink()
    with pytest.raises(ConfigurationError, match="indexed host file is missing"):
        load_inventory(config_root)


def test_unindexed_host_or_appliance_yaml_is_rejected(config_root: Path) -> None:
    extra_host = config_root / "hosts" / "extra.yaml"
    extra_host.write_text("host_id: extra\n")
    with pytest.raises(ConfigurationError, match="unindexed host YAML"):
        load_inventory(config_root)

    extra_host.unlink()
    (config_root / "appliances" / "extra.yml").write_text("appliance_id: extra\n")
    with pytest.raises(ConfigurationError, match="unindexed appliance YAML"):
        load_inventory(config_root)


@pytest.mark.parametrize("collection", ["host", "appliance"])
def test_filename_and_internal_id_mismatch_is_rejected(config_root: Path, collection: str) -> None:
    if collection == "host":
        path = config_root / "hosts" / "pi5.yaml"
        path.write_text(path.read_text().replace("host_id: pi5", "host_id: pi-five"))
    else:
        path = config_root / "appliances" / "home-assistant-green.yaml"
        path.write_text(
            path.read_text().replace(
                "appliance_id: home-assistant-green", "appliance_id: home-assistant"
            )
        )
    with pytest.raises(ConfigurationError, match="does not match internal ID"):
        load_inventory(config_root)


@pytest.mark.parametrize(
    "access",
    [
        "local",
        {"type": "serial"},
        {"type": "local", "host": "pi5"},
        {"type": "ssh", "host": ["pi5"]},
    ],
)
def test_malformed_access_shapes_are_rejected(config_root: Path, access: object) -> None:
    document = _read_host(config_root, "pi5")
    document["access"] = access
    _write_host(config_root, "pi5", document)

    with pytest.raises(ConfigurationError, match="access|SSH endpoint"):
        load_inventory(config_root)


def test_ssh_host_missing_endpoint_is_rejected(config_root: Path) -> None:
    document = _read_host(config_root, "pi5")
    document["access"] = {"type": "ssh"}
    _write_host(config_root, "pi5", document)
    with pytest.raises(ConfigurationError, match="missing required field: host"):
        load_inventory(config_root)


@pytest.mark.parametrize(
    ("host_id", "sudo", "message"),
    [
        ("yip-i3wm", "passwordless", "local host.*password_required"),
        ("pi5", "password_required", "SSH host.*passwordless"),
    ],
)
def test_contradictory_access_and_sudo_contract_is_rejected(
    config_root: Path, host_id: str, sudo: str, message: str
) -> None:
    document = _read_host(config_root, host_id)
    document["operator"]["sudo"] = sudo  # type: ignore[index]
    _write_host(config_root, host_id, document)
    with pytest.raises(ConfigurationError, match=message):
        load_inventory(config_root)


def test_duplicate_software_capability_id_across_categories_is_rejected(
    config_root: Path,
) -> None:
    document = _read_host(config_root, "pi5")
    document["software"]["components"] = {"apt": {}}  # type: ignore[index]
    _write_host(config_root, "pi5", document)
    with pytest.raises(ConfigurationError, match="duplicate software capability ID: apt"):
        load_inventory(config_root)


def test_duplicate_capability_mapping_key_is_rejected(config_root: Path) -> None:
    path = config_root / "hosts" / "pi5.yaml"
    path.write_text(path.read_text().replace("    apt: {}", "    apt: {}\n    apt: {}"))
    with pytest.raises(ConfigurationError, match="duplicate key 'apt'"):
        load_inventory(config_root)


def test_undeclared_update_mechanism_is_rejected(config_root: Path) -> None:
    document = _read_host(config_root, "pi5")
    document["management"]["homelab_update"]["mechanisms"].append("snap")  # type: ignore[index, union-attr]
    _write_host(config_root, "pi5", document)
    with pytest.raises(ConfigurationError, match="mechanism 'snap'.*not a declared"):
        load_inventory(config_root)


def test_missing_context_include_is_rejected(config_root: Path) -> None:
    document = _read_host(config_root, "pi5")
    document["context"] = {"include": ["exceptions/missing"]}
    _write_host(config_root, "pi5", document)
    with pytest.raises(
        ConfigurationError, match="cannot read context document 'exceptions/missing'"
    ):
        load_inventory(config_root)


@pytest.mark.parametrize("reference", ["../outside", "/tmp/outside", "exceptions\\outside"])
def test_context_traversal_and_unsafe_paths_are_rejected(config_root: Path, reference: str) -> None:
    document = _read_host(config_root, "pi5")
    document["context"] = {"include": [reference]}
    _write_host(config_root, "pi5", document)
    with pytest.raises(ConfigurationError, match="traversal|invalid path separator"):
        load_inventory(config_root)


def test_context_order_is_host_first_then_declared_includes(config_root: Path) -> None:
    extra = config_root / "context" / "exceptions" / "second.md"
    extra.write_text("# Second\n")
    document = _read_host(config_root, "yip-i3wm")
    document["context"] = {"include": ["exceptions/second", "exceptions/odysseus"]}
    _write_host(config_root, "yip-i3wm", document)
    inventory = load_inventory(config_root)

    context = load_host_context(config_root, inventory.host("yip-i3wm"))
    assert tuple(item.document_id for item in context.documents) == (
        "hosts/yip-i3wm",
        "exceptions/second",
        "exceptions/odysseus",
    )


def test_declared_capabilities_are_distinct_from_updater_scope(config_root: Path) -> None:
    inventory = load_inventory(config_root)
    vps = inventory.host("vps-strato")

    assert tuple(item.capability_id for item in vps.software.package_managers) == ("apt", "snap")
    assert vps.management.homelab_update.mechanisms == ("apt", "nextcloud_aio")
    for host in inventory.hosts:
        docker = next(item for item in host.software.runtimes if item.capability_id == "docker")
        assert docker.workload_desired_state_owner == "homelab-docker"


def test_central_config_has_no_docker_stack_membership(config_root: Path) -> None:
    for path in (config_root / "hosts").glob("*.yaml"):
        document = yaml.safe_load(path.read_text())
        assert "stacks" not in document
        assert "compose" not in document
        assert "managed_docker" not in document["management"]["homelab_update"]["mechanisms"]


def test_environment_and_explicit_config_root_precedence(
    config_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad_root = tmp_path / "bad"
    bad_root.mkdir()
    monkeypatch.setenv("HOMELAB_CONFIG_ROOT", str(bad_root))

    assert load_inventory(config_root).host_ids[0] == "yip-i3wm"
    with pytest.raises(ConfigurationError, match="does not contain inventory.yaml"):
        load_inventory()


def test_tilde_config_root_override_expands(
    config_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(config_root.parent))
    assert load_inventory(f"~/{config_root.name}").host_ids[0] == "yip-i3wm"


def test_default_root_does_not_depend_on_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HOMELAB_CONFIG_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert load_inventory().host_ids == ("yip-i3wm", "pi4", "pi5", "vps-strato")
