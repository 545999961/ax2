from __future__ import annotations

import os
import sys
from pathlib import Path


def command(repo_root: Path, dataset: str, *, mode: str = "direct", model: str = "", data_path: str = "", save_path: str = "", dry_run: bool = False, extra: list[str] | None = None) -> tuple[list[str], dict[str, str]]:
    script = repo_root / "vendor" / "research" / "eval_unified.py"
    if not script.is_file():
        raise FileNotFoundError(script)
    args = [sys.executable, str(script), "--datasets", dataset, "--mode", mode]
    if model:
        args += ["--model", model]
    if data_path:
        args += ["--data_path", data_path]
    if save_path:
        args += ["--save_path", save_path]
    if dry_run:
        args.append("--dry-run")
    args += list(extra or [])
    env = os.environ.copy()
    env["UNIFY_EVAL_ROOT"] = str(repo_root / "vendor" / "research")
    env["PYTHONPATH"] = str(repo_root / "vendor" / "research") + os.pathsep + env.get("PYTHONPATH", "")
    return args, env
