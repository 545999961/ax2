"""Dataset catalog shared by downloading and evaluation."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "configs/datasets.json").read_text())


def research_names() -> list[str]:
    return sorted(p.parent.name for p in (ROOT / "vendor/research/dataset_configs").glob("*/config.json"))


def canonical_name(value: str) -> str:
    normalized = value.strip().lower()
    compact = re.sub(r"[^a-z0-9]", "", normalized)
    for name in research_names():
        if normalized == name.lower() or compact == re.sub(r"[^a-z0-9]", "", name.lower()):
            return name
    for name, spec in CATALOG.items():
        aliases = [name, *spec.get("aliases", [])]
        if normalized in {str(alias).lower() for alias in aliases} or compact in {
            re.sub(r"[^a-z0-9]", "", str(alias).lower()) for alias in aliases
        }:
            return name
    raise ValueError(f"Unknown dataset {value!r}. Run: python -m arex_v2 list")


def data_root(value: str = "") -> Path:
    return Path(value or os.environ.get("AREX_DATA_ROOT") or ROOT / "data").expanduser().resolve()


def _bundled_config_path(name: str) -> Path | None:
    """Return the default path from a bundled evaluator config.

    The four downloadable datasets have entries in ``configs/datasets.json``.
    The remaining evaluator datasets are still valid selections, so they need
    the same path discovery and preflight checks instead of silently falling
    back to an opaque error inside the vendor evaluator.
    """
    config_path = ROOT / "vendor/research/dataset_configs" / name / "config.json"
    if not config_path.is_file():
        return None
    raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    value = str(raw.get("data_path") or "").replace(
        "${UNIFY_EVAL_ROOT}", str(ROOT / "vendor/research")
    )
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else (ROOT / "vendor/research" / path)


def dataset_paths(root: Path, names: list[str], *, use_legacy: bool = True) -> dict[str, str]:
    paths = {}
    for name in names:
        if name in CATALOG:
            spec = CATALOG[name]
            path = root / spec["path"]
            legacy = ROOT / spec["legacy_path"]
            if use_legacy and not path.exists() and legacy.exists():
                path = legacy
            paths[name] = str(path)
            continue
        bundled = _bundled_config_path(name)
        if bundled is not None:
            paths[name] = str(bundled)
    return paths


def path_is_ready(path: str | Path) -> bool:
    """Whether a prepared dataset path can be consumed by the evaluator."""
    candidate = Path(path)
    try:
        if candidate.is_file():
            return candidate.stat().st_size > 0
        # MoNaCo and a few vendor datasets are directories of traces or artifacts.
        return candidate.is_dir() and any(candidate.iterdir())
    except OSError:
        return False
