"""Strict safe YAML input with duplicate mapping-key detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode

from .errors import ConfigurationError


class UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate explicit keys and retains merge semantics."""


def _construct_unique_mapping(
    loader: UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    seen: set[Any] = set()
    for key_node, _ in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            continue
        key = loader.construct_object(key_node, deep=False)
        try:
            duplicate = key in seen
        except TypeError as error:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from error
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def safe_load_unique(text: str) -> Any:
    """Load YAML using only safe constructors and reject duplicate explicit keys."""

    return yaml.load(text, Loader=UniqueKeySafeLoader)


def load_yaml_file(path: Path, description: str) -> Any:
    """Read one required UTF-8 YAML file and normalize its errors."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigurationError(f"cannot read {description}: {path}") from error
    try:
        return safe_load_unique(text)
    except yaml.YAMLError as error:
        raise ConfigurationError(f"malformed YAML in {description} {path}: {error}") from error
