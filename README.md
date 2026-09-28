# AREX v2

AREX v2 is the single entry point for the evaluation code used by
`self_evolving_v15`. It combines the research benchmarks, Frontier-CS
algorithmic judge, and MLE-bench Lite runner without copying their large or
licensed datasets into Git.

- Chinese README: [README.zh-CN.md](README.zh-CN.md)
- Detailed configuration: [docs/configuration.md](docs/configuration.md)
- Evaluation and scoring: [docs/evaluation.md](docs/evaluation.md)
- Original upstream snapshots and licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

The command flow follows the same shape as the MiroThinker project: install,
prepare data, choose a benchmark, run a small smoke test, then inspect the
official score artifacts. See the upstream organization for reference:
[MiroThinker](https://github.com/MiroMindAI/MiroThinker).

## 1. Install

Python 3.10+ is required. Install only the extra needed by the evaluator:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[research]'       # BrowseComp/HLE/GAIA/DeepSearch-QA
# pip install -e '.[frontier]'     # Frontier-CS
# pip install -e '.[all]'          # all Python dependencies
python3 -m arex_v2 doctor
```

## 2. Prepare data with one command

```bash
python3 scripts/download_data.py --all
python3 scripts/download_data.py --list
```

The command downloads the public Frontier-CS problem archive into
`algorithmic/problems/`. Research datasets are shown by `--list` but are not
silently fetched: BrowseComp and HLE contain encrypted or licensed material,
and GAIA/DeepSearch-QA are distributed through their respective benchmark
channels. Put those files at the paths printed by `--list`, or pass a single
dataset-specific file with `--data-path`.

To pin a Frontier mirror and verify its archive:

```bash
python3 scripts/download_algorithmic.py \
  --url https://mirror.example/frontier-cs.tar.gz \
  --sha256 SHA256_HEX
```

## 3. Run an evaluation

The normal research command only needs a dataset name and a task count:

```bash
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

## 4. Model, search, and visit configuration

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

Research tools have a separate fixed contract:

```bash
export SERPER_API_KEY='...'   # search and Google Scholar
export JINA_API_KEY='...'     # visit; optional for public r.jina.ai
```

`search` uses Serper and `visit` uses Jina Reader. Optional endpoint overrides
are `SERPER_API_URL`, `SERPER_SCHOLAR_API_URL`, and `JINA_API_URL`. No key is
stored in this repository. A dry run checks command construction without
calling either service.

## 5. Repository map

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
```

Runtime data, result directories, credentials, and downloaded problem archives
are ignored by Git. Upstream notices and source versions are recorded in
`THIRD_PARTY_NOTICES.md` and `SNAPSHOT.txt`.

## 6. What to inspect after a run

Research runs write one directory per dataset under `--save-path`. Inspect each
case's `result.json` and aggregate the `score_result.score` values. Keep the
judge status, `official_scorer`, `judge_raw`, and error fields alongside the
numeric score. Frontier uses checker case scores; MLE-bench uses the host
grader. The complete per-task rules are in [docs/evaluation.md](docs/evaluation.md).

## 7. Useful commands

```bash
python3 -m arex_v2 list
python3 -m arex_v2 doctor
python3 scripts/download_data.py --list
python3 -m arex_v2 research BrowseComp --n 1 --dry-run
```

Do not commit benchmark files, API keys, model outputs, or local `.env` files.
