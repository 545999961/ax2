from __future__ import annotations

import os
import sys
from pathlib import Path


def command(
    repo_root: Path,
    datasets: str | list[str],
    *,
    mode: str = "direct",
    model: str = "",
    api_key_env: str = "API_KEY",
    base_url: str = "",
    data_path: str = "",
    save_path: str = "",
    num_tasks: int | None = None,
    start_index: int = 0,
    dry_run: bool = False,
    extra: list[str] | None = None,
) -> tuple[list[str], dict[str, str]]:
    script = repo_root / "vendor" / "research" / "eval_unified.py"
    if not script.is_file():
        raise FileNotFoundError(script)
    selected = [datasets] if isinstance(datasets, str) else list(datasets)
    if not selected or any(not item for item in selected):
        raise ValueError("at least one research dataset is required")
    if start_index < 0:
        raise ValueError("start_index must be zero or greater")
    args = [sys.executable, str(script), "--datasets", *selected, "--mode", mode]
    if model:
        args += ["--model", model]
    if data_path:
        args += ["--data_path", data_path]
    if save_path:
        args += ["--save_path", save_path]
    if start_index:
        args += ["--start_index", str(start_index)]
    if num_tasks is not None:
        if num_tasks <= 0:
            raise ValueError("num_tasks must be greater than zero")
        args += ["--end_index", str(start_index + num_tasks)]
    if dry_run:
        args.append("--dry-run")
    args += list(extra or [])
    env = os.environ.copy()
    # Keep secrets out of argv, shell history, and the command preview. The
    # evaluator reads these private bridge variables as parser defaults.
    if api_key_env:
        api_key = env.get(api_key_env, "")
        if api_key:
            env["AREX_SDK_API_KEY"] = api_key
    if base_url:
        env["AREX_SDK_BASE_URL"] = base_url
    if model:
        env["AREX_MODEL_NAME"] = model
    env["UNIFY_EVAL_ROOT"] = str(repo_root / "vendor" / "research")
    env["PYTHONPATH"] = str(repo_root / "vendor" / "research") + os.pathsep + env.get("PYTHONPATH", "")
    return args, env
