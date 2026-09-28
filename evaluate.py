#!/usr/bin/env python3
"""Run a research evaluation directly from a checkout.

This small wrapper keeps the common command discoverable without requiring an
editable install first.  The first argument is the dataset; all other options
are the same as ``python -m arex_v2 evaluate``.
"""

from __future__ import annotations

import sys

from arex_v2.cli import main


if __name__ == "__main__":
    main(["evaluate", *sys.argv[1:]])
