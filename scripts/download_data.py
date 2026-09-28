#!/usr/bin/env python3
"""Compatibility entry point for `python -m arex_v2 download`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arex_v2.cli import main

if __name__ == "__main__":
    main(["download", *sys.argv[1:]])
