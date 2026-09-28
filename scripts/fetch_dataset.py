#!/usr/bin/env python3
"""Fetch a research dataset into the path expected by the bundled evaluator."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arex_v2.data import download

DEFAULTS = {
    "BrowseComp": "datasets/BrowseComp/browse_comp_test_set.csv",
    "HLE": "hle_0724_vendor/data_json/text_items.jsonl",
    "GAIA-2023-validation-text-103": "datasets/GAIA/2023/validation-text-103/standardized_data.jsonl",
    "DeepSearch-QA": "datasets/DeepSearch-QA/DSQA-full.csv",
}

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("dataset", choices=sorted(DEFAULTS))
    p.add_argument("url")
    p.add_argument("--sha256", default="")
    p.add_argument("--destination", type=Path)
    ns=p.parse_args()
    root=Path(__file__).resolve().parents[1]/"vendor/research"
    dest=ns.destination or root/DEFAULTS[ns.dataset]
    print(download(ns.url,dest,ns.sha256))
if __name__ == "__main__": main()
