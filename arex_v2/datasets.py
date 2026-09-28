"""Dataset catalog shared by downloading and evaluation."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "configs/datasets.json").read_text())


def research_names() -> list[str]:
    return sorted(p.parent.name for p in (ROOT / "vendor/research/dataset_configs").glob("*/config.json"))


def canonical_name(value: str) -> str:
    for name in research_names():
        if value.lower() == name.lower():
            return name
    for name, spec in CATALOG.items():
        if value.lower() in spec["aliases"]:
            return name
    raise ValueError(f"Unknown dataset {value!r}. Run: python -m arex_v2 list")


def data_root(value: str = "") -> Path:
    return Path(value or os.environ.get("AREX_DATA_ROOT") or ROOT / "data").expanduser().resolve()


def dataset_paths(root: Path, names: list[str], *, use_legacy: bool = True) -> dict[str, str]:
    paths = {}
    for name in names:
        if name not in CATALOG:
            continue
        spec = CATALOG[name]
        path = root / spec["path"]
        legacy = ROOT / spec["legacy_path"]
        if use_legacy and not path.is_file() and legacy.is_file():
            path = legacy
        paths[name] = str(path)
    return paths
