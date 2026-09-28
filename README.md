# AREX Evaluation Suite

AREX is the evaluation checkout used by `self_evolving_v15`. It puts the
research benchmarks, their scorers, the Frontier-CS judge, and the MLE-bench
Lite runner behind one small command line interface. Benchmark data and model
outputs stay outside Git.

The usual path is deliberately short:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[research]'
cp configs/model.env.example .env
# edit .env, then load it into the shell
set -a; source .env; set +a

python3 -m arex_v2 list
python3 -m arex_v2 download BrowseComp
python3 evaluate.py BrowseComp --n 1 --dry-run
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10
```

`evaluate.py DATASET` and `python3 -m arex_v2 evaluate DATASET` are equivalent.
The dataset is the only positional choice. Add another dataset name to run
several datasets with the same model and task range:

```bash
python3 evaluate.py BrowseComp HLE --n 5 --save-path runs/smoke
```

## Before the first run

The model endpoint needs three settings:

| Setting | Example | Where it is read |
| --- | --- | --- |
| model | `provider/model-name` | `AREX_MODEL_NAME` |
| API key | `secret-value` | value of `MODEL_API_KEY` |
| base URL | `https://api.example.com/v1` | `AREX_BASE_URL` |

The command receives the **name** of the key variable (`MODEL_API_KEY` by
default), never the secret itself. Research runs also count tokens locally, so
set `AREX_TOKENIZER_PATH` to a tokenizer available to Transformers. Search and
page visits use `SERPER_API_KEY` and `JINA_API_KEY`; a dry run does not call
either service.

`configs/model.env.example` contains variable names only. Keep the edited
`.env` local; it is ignored by Git.

## Datasets

Run `python3 -m arex_v2 list` for the names accepted by the evaluator. The
download command prepares the four datasets with a public or Hugging Face
source:

| Dataset | Preparation | Per-case score |
| --- | --- | --- |
| BrowseComp | `python3 -m arex_v2 download BrowseComp` | BrowseComp official judge |
| DeepSearch-QA | `python3 -m arex_v2 download DeepSearch-QA` | DeepSearch-QA autorater |
| HLE | `python3 -m arex_v2 download HLE` after accepting HF terms and setting `HF_TOKEN` | HLE judge; `metrics.full_credit` |
| GAIA-2023-validation-text-103 | `python3 -m arex_v2 download GAIA-2023-validation-text-103` after setting `HF_TOKEN` | GAIA text judge |

The evaluator also contains configurations for `HLE-NoTool`,
`xBench-DeepSearch-2510`, the WideSearch variants, `DeepWideSearch`,
`MoNaCo`, `DeepResearch-Bench`, and `BrowseComp-Zh-official-en-prompt`.
Those datasets have their own licenses or source layouts; place the prepared
files at the path shown by `python3 -m arex_v2 download --list`, or pass
`--data-path` for one selected dataset. A missing path is reported before the
evaluator starts.

Use `--data-root PATH` to keep prepared data somewhere else. `--data-path PATH`
is intentionally limited to a single dataset so one file cannot accidentally
be used for several benchmarks.

## Selecting tasks and reading results

```bash
# rows [0, 20)
python3 evaluate.py BrowseComp --n 20

# rows [100, 120)
python3 evaluate.py BrowseComp --start-index 100 --n 20

# show the exact subprocess command without model, search, judge, or Docker calls
python3 evaluate.py BrowseComp --n 1 --dry-run
```

Each run creates one directory per dataset under `--save-path`. For research
benchmarks, inspect each case's `result.json`. Aggregate `score_result.score`
only after checking `status`, `official_scorer`, `judge_raw`, and any error
fields. Keep the model, endpoint, mode, task range, and Git commit with the
aggregate; scores from different settings are not directly comparable.

The detailed scoring rules and result examples are in
[docs/evaluation.md](docs/evaluation.md). Configuration details, including
advanced evaluator flags passed with repeated `--extra`, are in
[docs/configuration.md](docs/configuration.md). Chinese documentation is
available in [README.zh-CN.md](README.zh-CN.md).

## Other backends

The same CLI also exposes the two bundled non-research runners:

```bash
python3 scripts/download_data.py --dataset algorithmic
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker

MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
```

Use `python3 -m arex_v2 doctor` when checking a fresh checkout. The repository
map is kept small on purpose: `arex_v2/` contains the CLI and adapters,
`vendor/` contains upstream evaluator snapshots, `configs/` contains safe
examples, and `docs/` explains preparation and scoring. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [SNAPSHOT.txt](SNAPSHOT.txt)
for upstream versions and licenses.
