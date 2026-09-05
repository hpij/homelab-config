"""Resolve bounded host context documents without path guessing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from .errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .models import Host

_CONTEXT_PART = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True)
class ContextDocument:
    document_id: str
    content: str


@dataclass(frozen=True)
class ResolvedHostContext:
    host: Host
    documents: tuple[ContextDocument, ...]


def load_host_context(config_root: Path, host: Host) -> ResolvedHostContext:
    """Load the mandatory host document followed by declared includes."""

    document_ids = (f"hosts/{host.host_id}", *host.context.include)
    if len(set(document_ids)) != len(document_ids):
        raise ConfigurationError(f"host '{host.host_id}' has duplicate resolved context documents")
    documents = tuple(_load_document(config_root, document_id) for document_id in document_ids)
    return ResolvedHostContext(host, documents)


def validate_context_graph(config_root: Path, hosts: Iterable[Host]) -> None:
    """Resolve every host context reference to validate the complete graph."""

    for host in hosts:
        load_host_context(config_root, host)


def validate_context_id(document_id: str, *, subject: str) -> str:
    """Validate an extensionless repository-relative context document ID."""

    if not isinstance(document_id, str) or not document_id:
        raise ConfigurationError(f"{subject} must be a non-empty context document ID")
    if "\\" in document_id:
        raise ConfigurationError(f"{subject} contains an invalid path separator: {document_id}")
    path = PurePosixPath(document_id)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ConfigurationError(
            f"{subject} must not use absolute paths or traversal: {document_id}"
        )
    if len(path.parts) < 2 or any(_CONTEXT_PART.fullmatch(part) is None for part in path.parts):
        raise ConfigurationError(f"{subject} has an invalid context document ID: {document_id}")
    return document_id


def _load_document(config_root: Path, document_id: str) -> ContextDocument:
    validate_context_id(document_id, subject="context reference")
    context_root = (config_root / "context").resolve()
    path = (context_root / f"{document_id}.md").resolve()
    if not path.is_relative_to(context_root):
        raise ConfigurationError(f"context reference escapes the context directory: {document_id}")
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigurationError(f"cannot read context document '{document_id}': {path}") from error
    if not content.strip():
        raise ConfigurationError(f"context document '{document_id}' must not be empty")
    return ContextDocument(document_id, content)
