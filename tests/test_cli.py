from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
import yaml

from homelab_config.cli import main


def invoke(config_root: Path, arguments: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["--config-root", str(config_root), *arguments])
    return code, stdout.getvalue(), stderr.getvalue()


def test_list_hosts_and_appliances_are_in_exact_index_order(config_root: Path) -> None:
    code, stdout, stderr = invoke(config_root, ["list-hosts", "--json", "compact"])
    assert code == 0
    assert stderr == ""
    assert json.loads(stdout) == {
        "schema_version": 1,
        "hosts": ["yip-i3wm", "pi4", "pi5", "vps-strato"],
    }

    code, stdout, stderr = invoke(config_root, ["list-appliances", "--json", "compact"])
    assert code == 0
    assert stderr == ""
    assert json.loads(stdout) == {
        "schema_version": 1,
        "appliances": ["home-assistant-green"],
    }


@pytest.mark.parametrize("json_arguments", [["--json", "compact"], ["--json=compact"]])
def test_resolve_host_exact_ssh_compatibility_contract(
    config_root: Path, json_arguments: list[str]
) -> None:
    code, stdout, stderr = invoke(config_root, ["resolve-host", "vps-strato", *json_arguments])
    assert code == 0
    assert stderr == ""
    assert stdout == (
        '{"schema_version":1,"status":"ready","exit_code":0,"host_id":"vps-strato",'
        '"access":"ssh","ssh_target":"yip@vps"}\n'
    )
    assert json.loads(stdout) == {
        "schema_version": 1,
        "status": "ready",
        "exit_code": 0,
        "host_id": "vps-strato",
        "access": "ssh",
        "ssh_target": "yip@vps",
    }


def test_resolve_local_host_has_null_ssh_target(config_root: Path) -> None:
    code, stdout, stderr = invoke(config_root, ["resolve-host", "yip-i3wm", "--json", "compact"])
    assert code == 0
    assert stderr == ""
    assert json.loads(stdout)["ssh_target"] is None


@pytest.mark.parametrize("json_arguments", [["--json", "compact"], ["--json=compact"]])
def test_resolve_host_rejects_endpoint_alias_with_clean_json(
    config_root: Path, json_arguments: list[str]
) -> None:
    code, stdout, stderr = invoke(config_root, ["resolve-host", "vps", *json_arguments])
    document = json.loads(stdout)

    assert code == 30
    assert stderr.startswith("error: unknown canonical host ID: vps")
    assert document == {
        "schema_version": 1,
        "status": "fatal",
        "exit_code": 30,
        "error_code": "SELECTION_ERROR",
        "message": "unknown canonical host ID: vps",
    }
    assert "error:" not in stdout


def test_show_single_host_excludes_other_hosts_and_context(config_root: Path) -> None:
    code, stdout, stderr = invoke(config_root, ["show", "pi5", "--json", "compact"])
    document = json.loads(stdout)

    assert code == 0
    assert stderr == ""
    assert [item["host_id"] for item in document["hosts"]] == ["pi5"]
    assert "context" not in document["hosts"][0]
    assert "managed_workloads_owner" in stdout
    assert "workload_desired_state_owner" not in stdout
    assert "content" not in stdout
    assert "pi4" not in stdout


def test_show_omitted_and_explicit_subset_selection(config_root: Path) -> None:
    code, stdout, _ = invoke(config_root, ["show", "--json", "compact"])
    assert code == 0
    assert [item["host_id"] for item in json.loads(stdout)["hosts"]] == [
        "yip-i3wm",
        "pi4",
        "pi5",
        "vps-strato",
    ]

    code, stdout, _ = invoke(config_root, ["show", "pi5", "pi4", "--json", "compact"])
    assert code == 0
    assert [item["host_id"] for item in json.loads(stdout)["hosts"]] == ["pi5", "pi4"]


def test_show_json_omits_optional_management_when_absent(config_root: Path) -> None:
    path = config_root / "hosts" / "pi5.yaml"
    document = yaml.safe_load(path.read_text())
    document.pop("management")
    path.write_text(yaml.safe_dump(document, sort_keys=False))

    code, stdout, stderr = invoke(config_root, ["show", "pi5", "--json", "compact"])
    shown = json.loads(stdout)["hosts"][0]
    assert code == 0
    assert stderr == ""
    assert "management" not in shown


def test_context_single_host_is_bounded_and_ordered(config_root: Path) -> None:
    code, stdout, stderr = invoke(config_root, ["context", "pi5", "--json", "compact"])
    document = json.loads(stdout)

    assert code == 0
    assert stderr == ""
    assert len(document["hosts"]) == 1
    assert document["hosts"][0]["configuration"]["host_id"] == "pi5"
    assert [item["document_id"] for item in document["hosts"][0]["context"]] == ["hosts/pi5"]
    assert "vps-strato" not in stdout


@pytest.mark.parametrize(
    ("host_id", "expected_documents"),
    [
        ("vps-strato", ["hosts/vps-strato", "exceptions/nextcloud-aio"]),
        ("yip-i3wm", ["hosts/yip-i3wm", "exceptions/odysseus"]),
    ],
)
def test_context_includes_declared_exception(
    config_root: Path, host_id: str, expected_documents: list[str]
) -> None:
    code, stdout, _ = invoke(config_root, ["context", host_id, "--json", "compact"])
    assert code == 0
    assert [item["document_id"] for item in json.loads(stdout)["hosts"][0]["context"]] == (
        expected_documents
    )


def test_resolve_appliance_is_separate_and_versioned(config_root: Path) -> None:
    code, stdout, stderr = invoke(
        config_root,
        ["resolve-appliance", "home-assistant-green", "--json", "compact"],
    )
    assert code == 0
    assert stderr == ""
    assert json.loads(stdout) == {
        "schema_version": 1,
        "status": "ready",
        "exit_code": 0,
        "appliance_id": "home-assistant-green",
        "kind": "home_assistant",
        "name": "Home Assistant Green",
        "access": "ssh",
        "ssh_target": "hassio@homeassistant.local",
    }


def test_json_full_and_compact_differ_only_in_formatting(config_root: Path) -> None:
    compact = invoke(config_root, ["show", "pi4", "--json", "compact"])[1]
    full = invoke(config_root, ["show", "pi4", "--json", "full"])[1]

    assert json.loads(compact) == json.loads(full)
    assert '\n  "hosts"' in full
    assert '\n  "hosts"' not in compact


def test_invalid_configuration_json_stdout_is_valid_and_diagnostics_are_separate(
    config_root: Path,
) -> None:
    (config_root / "hosts" / "pi5.yaml").unlink()
    code, stdout, stderr = invoke(config_root, ["show", "pi5", "--json", "compact"])

    assert code == 30
    assert json.loads(stdout)["error_code"] == "CONFIGURATION_ERROR"
    assert stderr.startswith("error:")
    assert "error:" not in stdout


@pytest.mark.parametrize("json_arguments", [["--json", "compact"], ["--json=compact"]])
def test_configuration_failure_json_spellings_are_identical(
    config_root: Path, json_arguments: list[str]
) -> None:
    (config_root / "hosts" / "pi5.yaml").unlink()
    code, stdout, stderr = invoke(config_root, ["show", "pi5", *json_arguments])

    assert code == 30
    assert json.loads(stdout) == {
        "schema_version": 1,
        "status": "fatal",
        "exit_code": 30,
        "error_code": "CONFIGURATION_ERROR",
        "message": "indexed host file is missing: " + str(config_root / "hosts" / "pi5.yaml"),
    }
    assert stderr.startswith("error:")
    assert "error:" not in stdout


def test_config_root_override_works_from_an_unrelated_cwd(
    config_root: Path, tmp_path: Path
) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "homelab_config",
            "--config-root",
            str(config_root),
            "validate",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == "Configuration valid: 4 hosts, 1 appliance.\n"
    assert result.stderr == ""


def test_installed_console_entrypoint_smoke(config_root: Path) -> None:
    executable = Path(sys.executable).parent / "homelab-config"
    result = subprocess.run(
        [
            executable,
            "--config-root",
            config_root,
            "resolve-host",
            "pi5",
            "--json",
            "compact",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["ssh_target"] == "pi@pi5"
    assert result.stderr == ""
