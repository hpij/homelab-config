from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture
def config_root(tmp_path: Path) -> Path:
    project_root = Path(__file__).resolve().parents[1]
    shutil.copy2(project_root / "inventory.yaml", tmp_path / "inventory.yaml")
    for directory in ("hosts", "appliances", "context"):
        shutil.copytree(project_root / directory, tmp_path / directory)
    return tmp_path
