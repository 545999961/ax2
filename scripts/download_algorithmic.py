#!/usr/bin/env python3
"""Download Frontier-CS algorithmic problems on demand.

The repository intentionally does not carry the multi-gigabyte problem set. This
script downloads a GitHub source archive and extracts only algorithmic/problems.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from arex_v2.data import download, extract_tar, extract_zip  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="weiwch/Frontier-CS-Algo")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--url", default="")
    parser.add_argument("--archive", type=Path, default=ROOT / ".cache/frontier-cs-algo.tar.gz")
    parser.add_argument("--sha256", default="")
    parser.add_argument("--destination", type=Path, default=ROOT / "algorithmic")
    ns = parser.parse_args()
    url = ns.url or f"https://github.com/{ns.repo}/archive/refs/heads/{ns.ref}.tar.gz"
    archive = ns.archive
    if not archive.exists():
        print(f"downloading {url}")
        download(url, archive, ns.sha256)
    prefix = f"{ns.repo.split('/')[-1]}-{ns.ref}/algorithmic/problems/"
    destination = ns.destination / "problems"
    try:
        extract_tar(archive, destination, prefix=prefix)
    except tarfile.ReadError:
        with zipfile.ZipFile(archive) as z:
            names = [n for n in z.namelist() if "/algorithmic/problems/" in n]
            if not names:
                raise ValueError("archive does not contain algorithmic/problems")
            first = names[0].split("/algorithmic/problems/")[0] + "/algorithmic/problems/"
            extract_zip(archive, destination, prefix=first)
    print(f"algorithmic problems ready at {ns.destination / 'problems'}")


if __name__ == "__main__":
    main()
