<div align="center">

<img src="assets/arex-official.png" alt="AREX" width="420" />

<p><strong>Research, algorithmic programming, and machine learning evaluation</strong></p>

<a href="README.zh-CN.md">中文文档</a> · <a href="docs/evaluation.md">Evaluation</a> · <a href="docs/configuration.md">Configuration</a> · <a href="https://545999961.github.io/ax2/">Project site</a>

<br />

<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
<img src="https://img.shields.io/badge/Research-BrowseComp%20%7C%20HLE-16A085" alt="Research benchmarks" />
<img src="https://img.shields.io/badge/Programming-Frontier--CS-6C5CE7" alt="Frontier-CS" />
<img src="https://img.shields.io/badge/ML-MLE--bench-F59E0B" alt="MLE-bench" />

</div>

AREX is the evaluation checkout used by `self_evolving_v15`. It keeps the
research evaluators, Frontier-CS judge, and MLE-bench Lite runner in one
repository. Large, gated, encrypted, or licensed benchmark files stay outside
Git.

## Results at a glance

The checked-in chart is a project snapshot across the three evaluation tracks.
It is an SVG so it remains readable in GitHub and can be reused in reports.

![AREX benchmark results](assets/performance/arex-v2-benchmark-results.svg)

The numbers are comparable only when the model endpoint, task range, tools, and
judge settings are recorded with the run. The commands below reproduce the
evaluation workflow; [docs/evaluation.md](docs/evaluation.md) defines the
scoring signal for each track.

## What this repository evaluates

| Track | Benchmark | What is measured | Entry point |
| --- | --- | --- | --- |
| Research | BrowseComp, HLE, GAIA, DeepSearch-QA and related sets | Search, browsing, long-horizon reasoning | `python3 evaluate.py DATASET` |
| Algorithmic programming | Frontier-CS | C++17 solutions against checker cases | `python3 -m arex_v2 algorithmic ...` |
| Machine learning | MLE-bench Lite | Competition submissions and host-grader scores | `python3 -m arex_v2 mle ...` |

Use `python3 -m arex_v2 list` to see every registered research dataset.
Dataset selection is kept at the repository boundary: choose the dataset, and
the wrapper selects its bundled evaluator and data path.

## Quick start

### 1. Install

Python 3.10+ is required. Create an environment and install the extra for the
track you will run:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -e '.[research]'    # research benchmarks
# pip install -e '.[frontier]'  # Frontier-CS
# pip install -e '.[all]'       # all Python dependencies

python3 -m arex_v2 doctor
```

### 2. Prepare data

```bash
# list the state of every registered research dataset
python3 -m arex_v2 download --list

# prepare one research dataset
python3 -m arex_v2 download BrowseComp

# prepare research data plus the public Frontier-CS archive
python3 -m arex_v2 download --all
```

BrowseComp and DeepSearch-QA use public publisher files. HLE and GAIA require
accepting their Hugging Face terms and setting `HF_TOKEN`. Preparation is
incremental: a failed download does not remove datasets that are already ready.

Frontier-CS problems are placed in `algorithmic/problems/`. To use a pinned
mirror and checksum:

```bash
python3 scripts/download_algorithmic.py \
  --url https://mirror.example/frontier-cs.tar.gz \
  --sha256 SHA256_HEX
```

### 3. Configure the model

Copy the safe example, fill in local values, and load it into the shell:

```bash
cp configs/model.env.example .env
# edit .env
set -a; source .env; set +a
```

Research runs use `AREX_MODEL_NAME`, the key stored in `MODEL_API_KEY`, and
an optional `AREX_BASE_URL`. They also need a local
`AREX_TOKENIZER_PATH`. Search and page visits use `SERPER_API_KEY` and
`JINA_API_KEY`. Secrets are read from the environment and are never put in
argv or committed.

### 4. Run an evaluation

For research, the dataset is the only positional choice:

```bash
# inspect the constructed command without contacting any service
python3 evaluate.py BrowseComp --n 1 --dry-run

# evaluate rows [0, 10)
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10

# evaluate rows [100, 120)
python3 evaluate.py BrowseComp --start-index 100 --n 20

# run the same range for two datasets
python3 evaluate.py BrowseComp HLE --n 5 --save-path runs/smoke
```

The equivalent module command is `python3 -m arex_v2 evaluate BrowseComp`;
`research` and `eval` remain accepted aliases. Use `--data-root PATH` for
a separate data directory and `--data-path PATH` for one selected dataset.
The wrapper checks the selected path before launching the vendor evaluator.

For the two other tracks:

```bash
# Frontier-CS: problem id and a C++17 solution
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker

# MLE-bench Lite: prepare, run, then grade with the host grader
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
MLE_BENCH=$HOME/mle-bench \
  bash vendor/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
```

## What to inspect after a run

Research writes one `result.json` per case under
`<save-path>/<dataset>/`. Aggregate `score_result.score` only after checking
`status`, `official_scorer`, `judge_raw`, and error fields. Frontier-CS
uses checker case scores and MLE-bench uses the host grader fields in
`grade.log`. Keep the model, endpoint, task range, mode, Git commit, and data
checksum with every reported number.

Detailed scoring rules are in [docs/evaluation.md](docs/evaluation.md), and
advanced options are in [docs/configuration.md](docs/configuration.md). The
Chinese guide is [README.zh-CN.md](README.zh-CN.md). Upstream versions and
licenses are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and
[SNAPSHOT.txt](SNAPSHOT.txt).

## Repository map

```text
arex_v2/                  CLI, dataset catalog, and backend adapters
vendor/research/          research evaluator and dataset configurations
vendor/frontier_cs/       Frontier-CS Python snapshot
vendor/mle_lite/          MLE-bench Lite harness snapshot
algorithmic/              Frontier-CS judge and runtime files
scripts/                  data preparation and diagnostics
configs/                  safe local configuration examples
docs/                     configuration and scoring guides
assets/                   logo and benchmark artwork
site/                     static project homepage
```

Runtime data, credentials, result directories, and downloaded problem archives
are ignored by Git.
