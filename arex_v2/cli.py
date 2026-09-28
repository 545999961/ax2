from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .backends import frontier, mle, research

ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], env: dict[str, str], dry_run: bool) -> int:
    print("$", " ".join(_quote(x) for x in args))
    if dry_run:
        return 0
    return subprocess.run(args, env=env, cwd=ROOT).returncode


def _quote(value: str) -> str:
    return value if value and all(c.isalnum() or c in "-._/:=@" for c in value) else repr(value)


def doctor(_: argparse.Namespace) -> int:
    checks = {
        "research evaluator": ROOT / "vendor/research/eval_unified.py",
        "Frontier source": ROOT / "vendor/frontier_cs/frontier_cs/cli.py",
        "algorithmic launcher": ROOT / "algorithmic/README.md",
        "MLE Lite harness": ROOT / "vendor/mle_lite/scripts/run_one.sh",
    }
    for name, path in checks.items():
        print(f"{'OK' if path.exists() else 'MISSING':7} {name:24} {path}")
    for tool in ("python3", "docker", "uv", "node"):
        print(f"{'OK' if shutil.which(tool) else 'optional':7} command {tool}")
    return 0 if all(p.exists() for p in checks.values()) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arex", description="Unified AREX v2 evaluation CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check the assembled repository")
    sub.add_parser("list", help="list available backends")
    p = sub.add_parser("research", help="BrowseComp/HLE/GAIA/DeepSearchQA runner")
    p.add_argument("dataset", choices=["BrowseComp", "HLE", "GAIA-2023-validation-text-103", "DeepSearch-QA"])
    p.add_argument("--mode", default="direct", choices=["direct", "refine_summary", "return"])
    p.add_argument("--model", default="")
    p.add_argument("--data-path", default="")
    p.add_argument("--save-path", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--extra", action="append", default=[], help="pass an extra evaluator flag (repeatable)")
    p = sub.add_parser("algorithmic", help="Frontier-CS C++ solution evaluation")
    p.add_argument("problem", help="numeric problem id")
    p.add_argument("solution", help="path to a C++17 solution")
    p.add_argument("--backend", choices=["docker", "skypilot"], default="")
    p.add_argument("--judge-url", default="")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("mle", help="MLE-bench Lite one-competition runner")
    p.add_argument("competition", help="competition id, e.g. leaf-classification")
    p.add_argument("--prepare", action="store_true")
    p.add_argument("--time-limit", type=int, default=14400)
    p.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    ns = build_parser().parse_args(argv)
    if ns.command == "doctor":
        raise SystemExit(doctor(ns))
    if ns.command == "list":
        print("research: BrowseComp, HLE, GAIA-2023-validation-text-103, DeepSearch-QA")
        print("algorithmic: Frontier-CS algorithmic problems (C++17)")
        print("mle: MLE-bench Lite competitions through vendor/mle_lite")
        return
    if ns.command == "research":
        args, env = research.command(ROOT, ns.dataset, mode=ns.mode, model=ns.model, data_path=ns.data_path, save_path=ns.save_path, dry_run=ns.dry_run, extra=ns.extra)
        raise SystemExit(_run(args, env, ns.dry_run))
    if ns.command == "algorithmic":
        args, env = frontier.command(ROOT, ns.problem, ns.solution, backend=ns.backend, judge_url=ns.judge_url, dry_run=ns.dry_run)
        raise SystemExit(_run(args, env, ns.dry_run))
    if ns.command == "mle":
        args, env = mle.command(ROOT, ns.competition, prepare=ns.prepare, time_limit=ns.time_limit, dry_run=ns.dry_run)
        if ns.dry_run:
            print("(the MLE script still needs MLE_BENCH and prepared data for a real run)")
        raise SystemExit(_run(args, env, ns.dry_run))
