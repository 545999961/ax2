# Experiments and reproducibility

This directory holds commands that prepare data and run auxiliary experiments. The evaluator itself stays in `evaluation/`; dataset contracts stay in `data/`.

```text
configs/       safe local environment template
doctor.py      repository diagnostics
download_*.py  data preparation entrypoints
algorithmic/   Frontier-CS solution-generation experiments
```

The normal research path is still short:

```bash
python3 evaluate.py DATASET --n 10 --save-path runs/example
```

Use `--dry-run` first. A research run writes the model name, endpoint, Git
commit, task range, evaluator mode, and data checksum to `run_metadata.json`
and every case result. API keys belong in the shell environment and never in
command-line arguments or result files.

Compile the maintained Python entrypoints from the root:

```bash
python3 -m compileall -q evaluation/arex_v2 evaluation/research_eval/unified_eval scripts
```
