# Configuration

The top-level CLI keeps the common options small. Dataset-specific options stay
in `vendor/research/eval_unified.py` and can be passed with repeatable
`--extra` arguments.

## Common research options

```text
research DATASET [DATASET ...]
  --n / --num-tasks N       select N rows
  --start-index I           zero-based first row (default 0)
  --mode direct|refine_summary|return
  --model-name NAME         provider model identifier
  --api-key-env ENV_NAME    name of the environment variable holding the key
  --base-url URL             OpenAI-compatible model endpoint
  --data-path PATH          override the data file (one dataset only)
  --data-root PATH          prepared data root (default: ./data)
  --save-path PATH          result root
  --extra FLAG              pass one evaluator-specific flag; repeat it
```

For example, these options select rows 100 through 119 and limit concurrent
cases to four:

```bash
python3 -m arex_v2 research BrowseComp \
  --start-index 100 --n 20 \
  --extra=--concurrency_limit=4
```

The value of `--api-key-env` is a variable name, not the secret itself. The
adapter copies that variable into an internal process environment variable;
the secret is never appended to the command preview. `--model-name` and
`--base-url` are safe to show in logs because they are not credentials.

## Environment variables

| Variable | Used by | Required when |
| --- | --- | --- |
| `MODEL_API_KEY` (or another name selected by `--api-key-env`) | model SDK | any real model call |
| `SERPER_API_KEY` | `search`, `google_scholar` | research tools use Serper |
| `JINA_API_KEY` | `visit` | private/rate-limited Jina endpoint |
| `SERPER_API_URL` | Serper adapter | custom search endpoint |
| `SERPER_SCHOLAR_API_URL` | Serper Scholar adapter | custom Scholar endpoint |
| `JINA_API_URL` | Jina adapter | custom Reader endpoint |
| `MLE_BENCH` | MLE-bench Lite | MLE prepare/run |
| `HF_TOKEN` | Hugging Face gated downloader | HLE/GAIA preparation after access approval |
| `AREX_TOKENIZER_PATH` | local tokenizer | research token counting |
| provider-specific keys | Frontier/MLE adapters | according to the selected backend |

`configs/model.env.example` contains names and placeholders only. Keep real
values in a local ignored file or a secret manager.

## Dataset paths

The canonical prepared paths are under `data/`; legacy paths in
`vendor/research/datasets/` remain accepted when `--data-root` is omitted. The
dataset defaults are defined in
`vendor/research/dataset_configs/*/config.json`:

| Dataset | Default input |
| --- | --- |
| BrowseComp | `data/BrowseComp/browse_comp_test_set.csv` |
| HLE | `data/HLE/text_items.jsonl` |
| GAIA-2023-validation-text-103 | `data/GAIA-2023-validation-text-103/standardized_data.jsonl` |
| DeepSearch-QA | `data/DeepSearch-QA/DSQA-full.csv` |

Use `--data-path` for one selected dataset. The evaluator rejects a single path
override for a multi-dataset run rather than applying the wrong file to every
dataset.

## Advanced evaluator options

The underlying evaluator accepts flags such as:

```bash
python3 -m arex_v2 research HLE --n 20 \
  --extra=--concurrency_limit=8 \
  --extra=--hle-max-completion-tokens=32768 \
  --extra=--disable-visit-fallback
```

For a full list, run:

```bash
python3 vendor/research/eval_unified.py --help
```

Use `--dry-run` first. A dry run prints the constructed subprocess command and
does not call a model, Serper, Jina, judge, or Docker.

## Results and reruns

Set a unique `--save-path` for each model, mode, and task range. A research run
creates `<save-path>/<dataset>/.../result.json`. The default evaluator skip mode
is `correct`; use `--extra=--skip-existing-mode=none` when intentionally rerunning
all selected cases. Do not mix different model endpoints in one result root.
