# AREX v2 unified evaluation repository

This repository is the publishable, single entrypoint for the evaluation work in
`self_evolving_v15`. It keeps the four research evaluators, Frontier-CS
algorithmic evaluation, and MLE-bench Lite in one tree while preserving each
backend's own runtime contract.

The large Frontier-CS problem archive is deliberately excluded from Git. Run
this once when an algorithmic benchmark is needed:

```bash
python3 scripts/download_algorithmic.py
```

The downloader writes only `algorithmic/problems/`; it validates
archive paths and accepts `--url`/`--sha256` for a pinned mirror. This keeps a
normal GitHub clone small and lets a clean worker fetch the data at runtime.

## Layout

```text
arex_v2/                 stdlib-only CLI and subprocess adapters
vendor/frontier_cs/      Frontier-CS Python package snapshot
vendor/harbor_pi_supported/ Harbor runtime source snapshot
algorithmic/              Frontier-CS judge and scripts; problems downloaded on demand
vendor/mle_lite/         MLE-bench Lite pi harness snapshot
vendor/research/         BrowseComp/HLE/GAIA/DeepSearchQA evaluator and configs
scripts/                 data download and diagnostics helpers
reference/               original 0919 runner scripts for reproducibility
```

Run `python3 -m arex_v2 list` or `python3 -m arex_v2 doctor` first. The CLI
never stores credentials in the repository. Model API credentials remain in the
provider environment or Pi's existing auth file.

## Unified commands

```bash
# Validate paths and optional tools
python3 -m arex_v2 doctor

# Check the exact command without making a model or Docker call
python3 -m arex_v2 research BrowseComp --dry-run
python3 -m arex_v2 algorithmic 1 solution.cpp --dry-run
python3 -m arex_v2 mle leaf-classification --dry-run
```

### Research: BrowseComp, HLE, GAIA, DeepSearchQA

The evaluator uses the bundled `vendor/research/eval_unified.py`. Supply the
same data files and model endpoint used by the original runs:

```bash
python3 -m arex_v2 research HLE \
  --mode refine_summary --model provider/model \
  --data-path /path/to/text_items.jsonl --save-path runs/hle
```

Use `scripts/fetch_dataset.py DATASET URL` when a dataset is hosted at a
known, approved URL. The script supports `--sha256`; no URL or credential is
invented by the repository.

### Frontier-CS algorithmic

Solutions are C++17 files. After downloading problems, the adapter exposes the
original Frontier CLI and sets `FRONTIER_CS_ALGORITHMIC_PATH` to the unified
`algorithmic/` directory:

```bash
python3 scripts/download_algorithmic.py
python3 -m arex_v2 algorithmic 1 solution.cpp --backend docker
```

The bundled Harbor source is available under `vendor/harbor_pi_supported/`. The Frontier and Docker/SkyPilot dependencies are optional; they are listed in
`pyproject.toml` and are not imported by the stdlib-only CLI until this backend
is actually run.

### MLE-bench Lite

The MLE backend is the original self-contained pi harness. Set `MLE_BENCH` to
a checkout of OpenAI's `mle-bench`, prepare one competition, then run it:

```bash
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
```

The MLE scripts still require Docker, Kaggle data, and the model provider
credentials described in `vendor/mle_lite/README.md`.

## Reproducibility and licensing

`vendor/` contains source snapshots copied from the two requested GitHub
projects. Keep their upstream license and attribution files when publishing,
and record the exact upstream commit in your release notes. Evaluation data,
model outputs, credentials, and run directories are ignored by Git.
