"""Read-only command-line interface for canonical homelab configuration."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .context import load_host_context
from .errors import ConfigurationError, HomelabConfigError, SelectionError
from .inventory import load_inventory, select_hosts
from .render import (
    SCHEMA_VERSION,
    fatal_document,
    host_contexts_document,
    hosts_document,
    render_context_human,
    render_json,
    render_yaml,
    resolved_appliance_document,
    resolved_host_document,
)

JSON_MODES = ("compact", "full")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="homelab-config",
        description="Read canonical declared homelab configuration without runtime probing.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config-root",
        type=Path,
        help="configuration repository root (overrides HOMELAB_CONFIG_ROOT)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate", help="validate the complete configuration and context graph")

    list_hosts = commands.add_parser("list-hosts", help="list canonical host IDs in index order")
    _add_optional_json(list_hosts)

    show = commands.add_parser("show", help="show normalized declared host configuration")
    show.add_argument("hosts", nargs="*", metavar="HOST_ID")
    _add_optional_json(show)

    context = commands.add_parser("context", help="show host configuration and bounded context")
    context.add_argument("hosts", nargs="+", metavar="HOST_ID")
    _add_optional_json(context)

    resolve_host = commands.add_parser(
        "resolve-host", help="resolve exactly one canonical host transport identity"
    )
    resolve_host.add_argument("host_id", metavar="HOST_ID")
    _add_required_json(resolve_host)

    list_appliances = commands.add_parser(
        "list-appliances", help="list canonical appliance IDs in index order"
    )
    _add_optional_json(list_appliances)

    resolve_appliance = commands.add_parser(
        "resolve-appliance", help="resolve exactly one canonical appliance transport identity"
    )
    resolve_appliance.add_argument("appliance_id", metavar="APPLIANCE_ID")
    _add_required_json(resolve_appliance)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if arguments is None else arguments)
    json_mode = _requested_json_mode(args)
    parsed = build_parser().parse_args(args)
    try:
        inventory = load_inventory(parsed.config_root)
        if parsed.command == "validate":
            appliance_label = "appliance" if len(inventory.appliances) == 1 else "appliances"
            print(
                f"Configuration valid: {len(inventory.hosts)} hosts, "
                f"{len(inventory.appliances)} {appliance_label}."
            )
        elif parsed.command == "list-hosts":
            document = {"schema_version": SCHEMA_VERSION, "hosts": list(inventory.host_ids)}
            _print_json_or_lines(document, inventory.host_ids, parsed.json_mode)
        elif parsed.command == "show":
            selected = select_hosts(inventory, parsed.hosts)
            _print_document(hosts_document(selected), parsed.json_mode)
        elif parsed.command == "context":
            selected = select_hosts(inventory, parsed.hosts)
            contexts = tuple(
                load_host_context(Path(inventory.config_root), host) for host in selected
            )
            if parsed.json_mode:
                print(render_json(host_contexts_document(contexts), parsed.json_mode))
            else:
                print(render_context_human(contexts))
        elif parsed.command == "resolve-host":
            if parsed.host_id == "all":
                raise SelectionError("'all' is unsupported; resolve exactly one canonical HOST_ID")
            print(
                render_json(
                    resolved_host_document(inventory.host(parsed.host_id)), parsed.json_mode
                )
            )
        elif parsed.command == "list-appliances":
            document = {
                "schema_version": SCHEMA_VERSION,
                "appliances": list(inventory.appliance_ids),
            }
            _print_json_or_lines(document, inventory.appliance_ids, parsed.json_mode)
        else:
            if parsed.appliance_id == "all":
                raise SelectionError(
                    "'all' is unsupported; resolve exactly one canonical APPLIANCE_ID"
                )
            appliance = inventory.appliance(parsed.appliance_id)
            print(render_json(resolved_appliance_document(appliance), parsed.json_mode))
    except HomelabConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        if json_mode:
            print(render_json(fatal_document(_error_code(error), str(error)), json_mode))
        return 30
    return 0


def _add_optional_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", choices=JSON_MODES, dest="json_mode")


def _add_required_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", choices=JSON_MODES, dest="json_mode", required=True)


def _requested_json_mode(arguments: Sequence[str]) -> str | None:
    try:
        index = arguments.index("--json")
    except ValueError:
        return None
    if index + 1 < len(arguments) and arguments[index + 1] in JSON_MODES:
        return arguments[index + 1]
    return None


def _print_document(document: object, json_mode: str | None) -> None:
    print(render_json(document, json_mode) if json_mode else render_yaml(document))


def _print_json_or_lines(
    document: object,
    identifiers: tuple[str, ...],
    json_mode: str | None,
) -> None:
    if json_mode:
        print(render_json(document, json_mode))
    else:
        print("\n".join(identifiers))


def _error_code(error: HomelabConfigError) -> str:
    if isinstance(error, ConfigurationError):
        return "CONFIGURATION_ERROR"
    return "SELECTION_ERROR"


if __name__ == "__main__":
    raise SystemExit(main())
