# AREX-2 evaluation suite

AREX-2 is the evaluation checkout used by `self_evolving_v15`. It puts the research, Frontier-CS algorithmic, and MLE-bench Lite evaluation paths behind one small command line interface. Benchmark files, model outputs, and keys stay outside Git; the repository contains the runners, dataset definitions, and the commands needed to reproduce a run.

[中文说明](README.zh-CN.md) · [dataset-by-dataset protocol](data/README.md) · [experiment notes](scripts/README.md) · [project site](https://545999961.github.io/ax2/)

## Layout

```text
evaluation/   CLI, evaluation adapters, and the pinned evaluator snapshots
data/         dataset configs, preparation catalog, and per-dataset notes
assets/       benchmark PDF/SVG, logo files, and the static project site
scripts/      download scripts, run configs, algorithmic experiments, and tests
evaluate.py   short root-level wrapper for selecting research datasets
```

The important rule is that dataset-specific behavior lives in `data/<track>/<dataset>/`: `config.json` describes the input and output fields, `prompt.py` describes the model prompt, and `judge_local.py` or `judge_offical.py` defines the scorer when the benchmark has one. The complete matrix is in [data/README.md](data/README.md).

## Install

Python 3.10+ is required. Install only the dependencies for the track you need:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[research]'   # research benchmarks
# pip install -e '.[frontier]' # Frontier-CS
# pip install -e '.[all]'      # all Python dependencies
python3 -m arex_v2 doctor
```

## Research evaluation

List the registered datasets first:

```bash
python3 -m arex_v2 list
```

The outer interface only asks for a dataset. The wrapper resolves its config, data path, prompt, loader, and scorer before launching the evaluator:

```bash
# inspect the exact subprocess command, without credentials or network calls
python3 evaluate.py BrowseComp --n 1 --dry-run

# evaluate rows [0, 10)
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10

# evaluate rows [100, 120)
python3 evaluate.py HLE --start-index 100 --n 20

# run the same range for two datasets
python3 evaluate.py BrowseComp HLE --n 5 --save-path runs/smoke
```

Prepare the four datasets with a built-in download recipe:

```bash
python3 -m arex_v2 download BrowseComp
python3 -m arex_v2 download DeepSearch-QA
python3 -m arex_v2 download HLE                 # requires HF_TOKEN and access
python3 -m arex_v2 download GAIA-2023-validation-text-103  # requires HF_TOKEN
python3 -m arex_v2 download --list
```

By default files are stored under `data/files/`. Use `--data-root PATH` to keep them elsewhere, or `--data-path PATH` for one manually prepared dataset. The selected path is checked before a real run starts. Results are written to `runs/<timestamp>/<dataset>/`; inspect each case's `status`, `judge_raw`, and `score_result` before aggregating scores.

The per-dataset input format, prompt, judge, metric, and preparation command are documented in [data/README.md](data/README.md). Advanced CLI and environment options are in [evaluation/docs/configuration.md](evaluation/docs/configuration.md).

## Frontier-CS algorithmic evaluation

The source for the judge is in `evaluation/algorithmic/`; the downloaded problem set and run artifacts live in `data/algorithmic/`:

```bash
python3 -m arex_v2 download algorithmic
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker
```

Solutions are C++17 files. The checker reports per-case results and `scoreRatio`/`scoreRatioUnbounded`; see [data/algorithmic/README.md](data/algorithmic/README.md) for the input layout and judge lifecycle.

## MLE-bench Lite

```bash
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
MLE_BENCH=$HOME/mle-bench \
  bash evaluation/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
```

The final number comes from the host grader (`grade.log`), including `valid_submission` and the competition score. The runner and its upstream notes are kept in `evaluation/mle_lite/`.

## Results

![AREX benchmark results](assets/performance/arex-v2-benchmark-results.svg)

The source chart is [available as a PDF](assets/performance/arex-v2-benchmark-results.pdf). Record the Git commit, model, endpoint, task range, evaluator mode, and data checksum with every reported number.

## Checks

```bash
PYTHONPATH=evaluation python3 -m unittest discover -s evaluation/tests -v
python3 -m compileall -q evaluation/arex_v2 evaluation/research_eval/unified_eval scripts
```

Third-party origins and pinned snapshots are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [SNAPSHOT.txt](SNAPSHOT.txt).
