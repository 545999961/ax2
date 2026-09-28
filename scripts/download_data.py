#!/usr/bin/env python3
"""Prepare benchmark data through one stable entry point.

Public Frontier-CS problems can be downloaded automatically. The research
benchmarks are intentionally listed as local/gated datasets because several
are encrypted, license-restricted, or distributed through an evaluation
portal. This command never guesses a private URL or embeds credentials.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATASETS = {
    "algorithmic": ("downloadable", ROOT / "algorithmic/problems", "Frontier-CS-Algo public archive"),
    "BrowseComp": ("gated", ROOT / "vendor/research/datasets/BrowseComp/browse_comp_test_set.csv", "supply the licensed/encrypted CSV"),
    "HLE": ("gated", ROOT / "vendor/research/hle_0724_vendor/data_json/text_items.jsonl", "supply text_items.jsonl and attachments"),
    "GAIA-2023-validation-text-103": ("gated", ROOT / "vendor/research/datasets/GAIA/2023/validation-text-103/standardized_data.jsonl", "supply the validation set and attachments"),
    "DeepSearch-QA": ("gated", ROOT / "vendor/research/datasets/DeepSearch-QA/DSQA-full.csv", "supply DSQA-full.csv"),
}


def print_status() -> None:
    for name, (kind, path, note) in DATASETS.items():
        state = "ready" if path.exists() else "missing"
        print(f"{name:32} {state:7} {kind:11} {path} ({note})")


def download_algorithmic(dry_run: bool) -> int:
    command = [sys.executable, str(ROOT / "scripts/download_algorithmic.py")]
    print("$", " ".join(command))
    if dry_run:
        return 0
    return subprocess.run(command, cwd=ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public data and check gated benchmark data")
    parser.add_argument("--dataset", choices=["all", *DATASETS], default="all")
    parser.add_argument("--all", dest="download_all", action="store_true", help="download public data and report gated data")
    parser.add_argument("--list", action="store_true", help="show data status and exit")
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args()
    if ns.download_all:
        ns.dataset = "all"
    if ns.list:
        print_status()
        return 0
    if ns.dataset in ("all", "algorithmic"):
        code = download_algorithmic(ns.dry_run)
        if code:
            return code
    if ns.dataset == "all":
        print("\nResearch datasets are local/gated; no URL or credential was guessed.")
        print("Place each file at the path shown by: python3 scripts/download_data.py --list")
    elif ns.dataset != "algorithmic":
        _, path, note = DATASETS[ns.dataset]
        print(f"{ns.dataset}: {path}")
        print(f"Action: {note}; then rerun --list.")
    if not ns.dry_run:
        print_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
