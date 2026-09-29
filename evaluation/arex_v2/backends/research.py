from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

from ..datasets import data_root as resolve_data_root, dataset_paths, path_is_ready, research_names


def command(
    repo_root: Path, datasets: str | list[str], *, mode: str = "direct",
    model: str = "", api_key_env: str = "MODEL_API_KEY", base_url: str = "",
    data_path: str = "", save_path: str = "", data_root: str = "",
    tokenizer_path: str = "", num_tasks: int | None = None, start_index: int = 0,
    concurrency: int = 4, shuffle: bool = False,
    judge_model: str = "", judge_base_url: str = "", judge_api_key_env: str = "",
    summary_model: str = "", summary_base_url: str = "", summary_api_key_env: str = "",
    dry_run: bool = False, extra: list[str] | None = None,
) -> tuple[list[str], dict[str, str]]:
    selected = list(dict.fromkeys([datasets] if isinstance(datasets, str) else datasets))
    if not selected or start_index < 0 or (num_tasks is not None and num_tasks <= 0):
        raise ValueError("select a dataset, a nonnegative start index, and a positive task count")
    available = set(research_names())
    unknown = [name for name in selected if name not in available]
    if unknown:
        raise ValueError(
            "Unknown research dataset(s): " + ", ".join(unknown)
            + ". Run `python -m arex_v2 list` to see available datasets."
        )
    if data_path and len(selected) != 1:
        raise ValueError("--data-path requires exactly one dataset; use --data-root for multiple datasets")
    env = os.environ.copy()
    root = resolve_data_root(data_root)
    paths = dataset_paths(root, selected, use_legacy=not (data_root or env.get("AREX_DATA_ROOT")))
    if data_path:
        paths[selected[0]] = str(Path(data_path).expanduser().resolve())
    if not dry_run:
        for name in selected:
            path = paths.get(name)
            if not path or not path_is_ready(path):
                raise ValueError(f"Missing data for {name}. Run: python -m arex_v2 download {name}")
        if not model:
            raise ValueError("Set AREX_MODEL_NAME or --model-name")
        if not env.get(api_key_env):
            raise ValueError(f"Set the model key environment variable {api_key_env!r}")
        if any(name != "HLE" for name in selected) and not tokenizer_path:
            raise ValueError("Set AREX_TOKENIZER_PATH or --tokenizer-path to the agent model's tokenizer")
    for value in extra or []:
        if "api_key" in value.lower() or "api-key" in value.lower():
            raise ValueError("Pass keys through --api-key-env/--judge-api-key-env/--summary-api-key-env, not --extra")
    evaluator_root = repo_root / "evaluation/research_eval"
    args = [sys.executable, str(evaluator_root / "eval_unified.py"),
            "--datasets", *selected, "--mode", mode,
            "--start_index", str(start_index),
            "--end_index", str(start_index + num_tasks if num_tasks is not None else 9999999999999),
            "--concurrency_limit", str(concurrency)]
    # Explicit per-dataset ends bypass the legacy HLE default of only 200 tasks.
    end = start_index + num_tasks if num_tasks is not None else 9999999999999
    args += ["--dataset-end-indices", " ".join(f"{name}={end}" for name in selected)]
    if not shuffle:
        args.append("--no-shuffle")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output = Path(save_path).expanduser().resolve() if save_path else repo_root / "runs" / timestamp
    args += ["--save_path", str(output)]
    for flag, value in (("model", model), ("tokenizer_path", tokenizer_path),
                        ("judge_model", judge_model), ("judge_base_url", judge_base_url),
                        ("summary_model", summary_model), ("summary_base_url", summary_base_url)):
        if value:
            args += [f"--{flag}", value]
    # Keys remain in the subprocess environment, never in the command preview.
    for variable, source in (("AREX_SDK_API_KEY", api_key_env),
                             ("AREX_JUDGE_API_KEY", judge_api_key_env),
                             ("AREX_SUMMARY_API_KEY", summary_api_key_env)):
        if source:
            if not dry_run and not env.get(source):
                raise ValueError(f"Missing key environment variable {source!r}")
            env[variable] = env.get(source, "")
    if base_url:
        env["AREX_SDK_BASE_URL"] = base_url
    env["AREX_DATA_PATHS"] = json.dumps(paths)
    env["UNIFY_EVAL_ROOT"] = str(evaluator_root)
    env["AREX_DATASET_CONFIG_ROOT"] = str(repo_root / "data/research")
    env["AREX_DATA_ROOT"] = str(root)
    env["PYTHONPATH"] = str(evaluator_root) + os.pathsep + env.get("PYTHONPATH", "")
    if dry_run:
        args.append("--dry-run")
    args += list(extra or [])
    return args, env
