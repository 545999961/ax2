<div align="center">

<img src="assets/arex-official.png" alt="AREX" width="420" />

<p><strong>Unified agent research, search, reasoning, and benchmark evaluation</strong></p>

<a href="README.zh-CN.md">中文文档</a> · <a href="docs/evaluation.md">Evaluation</a> · <a href="docs/configuration.md">Configuration</a>

<br />

<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
<img src="https://img.shields.io/badge/Search-Serper-1D9BF0" alt="Serper search" />
<img src="https://img.shields.io/badge/Visit-Jina%20Reader-16A085" alt="Jina Reader visit" />
<img src="https://img.shields.io/badge/Data-on%20demand-F59E0B" alt="Data on demand" />

</div>

> **AREX Evaluation Suite** packages the research evaluators, data preparation,
> and benchmark runners in one reproducible entry point. The Python module
> remains `arex_v2`, so existing commands continue to work.

AREX Evaluation Suite is the single entry point for the evaluation code used by
`self_evolving_v15`. It combines the research benchmarks, Frontier-CS
algorithmic judge, and MLE-bench Lite runner without copying their large or
licensed datasets into Git.

The logo follows the official [AREX research site](https://arex-research.com/).

- Chinese README: [README.zh-CN.md](README.zh-CN.md)
- Homepage: [AREX Evaluation Suite](https://545999961.github.io/AREX-v2/)
- Detailed configuration: [docs/configuration.md](docs/configuration.md)
- Evaluation and scoring: [docs/evaluation.md](docs/evaluation.md)
- Original upstream snapshots and licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

## 📈 Performance snapshot

The checked-in chart is the current project comparison snapshot. It is kept as
an SVG so it stays sharp in the GitHub README and can be downloaded for reports.

![AREX benchmark results](assets/performance/arex-v2-benchmark-results.svg)

Scores are only comparable when the model endpoint, task range, tools, and
judge configuration are recorded with the run. See [Evaluation and scoring](docs/evaluation.md).

The command flow follows the same shape as the MiroThinker project: install,
prepare data, choose a benchmark, run a small smoke test, then inspect the
official score artifacts. See the upstream organization for reference:
[MiroThinker](https://github.com/MiroMindAI/MiroThinker).

<details>
<summary>Contents</summary>

- [Performance snapshot](#-performance-snapshot)
- [Quick start](#-quick-start)
- [Configuration](#-model-search-and-visit-configuration)
- [Repository map](#-repository-map)
- [Evaluation artifacts](#-what-to-inspect-after-a-run)

</details>

## 🚀 Quick start

### 1. Install

Python 3.10+ is required. Install only the extra needed by the evaluator:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[research]'       # BrowseComp/HLE/GAIA/DeepSearch-QA
# pip install -e '.[frontier]'     # Frontier-CS
# pip install -e '.[all]'          # all Python dependencies
python3 -m arex_v2 doctor
```

### 2. Prepare data with one command

```bash
python3 scripts/download_data.py --all
python3 scripts/download_data.py --list
# equivalent module form:
python3 -m arex_v2 download --all
```

The command downloads the public Frontier-CS problem archive into
`algorithmic/problems/` and prepares the core research datasets under `data/`.
BrowseComp and DeepSearch-QA have public publisher files; HLE and GAIA require
accepting their gated Hugging Face terms and setting `HF_TOKEN`. If a gated
download is unavailable, the command reports the missing dataset and leaves
all already completed downloads intact. Use `--list` to see the current state.

To pin a Frontier mirror and verify its archive:

```bash
python3 scripts/download_algorithmic.py \
  --url https://mirror.example/frontier-cs.tar.gz \
  --sha256 SHA256_HEX
```

### 3. Run an evaluation

The normal research command only needs a dataset name and a task count:

```bash
cp configs/model.env.example .env  # edit model/key/tokenizer values first
set -a; source .env; set +a
python3 -m arex_v2 research BrowseComp --n 10 --dry-run
python3 -m arex_v2 research BrowseComp --n 10 \
  --model provider/model-name \
  --api-key-env MODEL_API_KEY \
  --base-url https://api.example.com/v1 \
  --save-path runs/browsecomp-10
```

`--n 10` evaluates rows `[0, 10)`. Use `--start-index 100 --n 20` for rows
`[100, 120)`. Several datasets can share one run and the same range:

```bash
python3 -m arex_v2 research BrowseComp HLE --n 5 --save-path runs/smoke
```

`--data-path` is intentionally limited to one selected dataset because each
benchmark has a different file format. For multiple datasets, keep their
files at the default paths listed in the dataset configs, or pass per-dataset
options through `--extra`; see [docs/configuration.md](docs/configuration.md).

Other backends use the same top-level CLI:

```bash
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
```

## ⚙️ Model, search, and visit configuration

Every model-backed run has three independent endpoint settings:

| Setting | Example | Meaning |
| --- | --- | --- |
| model name | `provider/model-name` | model identifier sent to the provider |
| API key | `MODEL_API_KEY` | **environment variable name** containing the secret |
| base URL | `https://api.example.com/v1` | optional OpenAI-compatible endpoint |

The API key value is read from the environment and never put in argv, logs, or
the repository. Copy `configs/model.env.example` to a local ignored file if it
helps organize the variables. The evaluator uses `AREX_SDK_API_KEY`,
`AREX_SDK_BASE_URL`, and `AREX_MODEL_NAME` internally.

The agent also needs a local tokenizer for token counting. Set
`AREX_TOKENIZER_PATH` in the example file or add `--tokenizer-path PATH`; this
is independent of the served model endpoint.

Research tools have a separate fixed contract:

```bash
export SERPER_API_KEY='...'   # search and Google Scholar
export JINA_API_KEY='...'     # visit; optional for public r.jina.ai
```

`search` uses Serper and `visit` uses Jina Reader. Optional endpoint overrides
are `SERPER_API_URL`, `SERPER_SCHOLAR_API_URL`, and `JINA_API_URL`. No key is
stored in this repository. A dry run checks command construction without
calling either service.

## 🗂️ Repository map

```text
arex_v2/                  small stdlib-only CLI and backend adapters
vendor/research/          unified research evaluator and dataset configs
vendor/frontier_cs/       Frontier-CS Python source snapshot
vendor/mle_lite/          MLE-bench Lite harness snapshot
algorithmic/              Frontier judge; problems downloaded on demand
scripts/                  data preparation, download, and diagnostics
configs/                  safe configuration examples (no secrets)
reference/                original runners kept for reproducibility
docs/                     configuration and per-benchmark scoring guides
assets/                   logo, icons, and benchmark result artwork
site/                     static homepage and GitHub Pages workflow
```

Runtime data, result directories, credentials, and downloaded problem archives
are ignored by Git. Upstream notices and source versions are recorded in
`THIRD_PARTY_NOTICES.md` and `SNAPSHOT.txt`.

## ✅ What to inspect after a run

Research runs write one directory per dataset under `--save-path`. Inspect each
case's `result.json` and aggregate the `score_result.score` values. Keep the
judge status, `official_scorer`, `judge_raw`, and error fields alongside the
numeric score. Frontier uses checker case scores; MLE-bench uses the host
grader. The complete per-task rules are in [docs/evaluation.md](docs/evaluation.md).

## 🔧 Useful commands

```bash
python3 -m arex_v2 list
python3 -m arex_v2 doctor
python3 scripts/download_data.py --list
python3 -m arex_v2 research BrowseComp --n 1 --dry-run
python3 -m arex_v2 download DeepSearch-QA --dry-run
```

Do not commit benchmark files, API keys, model outputs, or local `.env` files.
