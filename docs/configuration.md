# Configuration

The repository wrapper keeps the common options small. Dataset-specific options
remain in `vendor/research/eval_unified.py` and can be passed with repeated
`--extra` arguments.

## Common options

```text
evaluate DATASET [DATASET ...]
  --n / --num-tasks N       number of rows
  --start-index I           zero-based first row (default 0)
  --mode direct|refine_summary|return
  --model NAME              provider model identifier
  --api-key-env ENV_NAME    environment variable containing the key
  --base-url URL             OpenAI-compatible model endpoint
  --data-path PATH           override one selected dataset's input
  --data-root PATH           prepared data root (default: ./data)
  --save-path PATH           result root (default: runs/<timestamp>)
  --concurrency N            maximum concurrent cases (default: 4)
  --extra FLAG               evaluator-specific flag; repeat it
```

For example:

```bash
python3 evaluate.py BrowseComp --start-index 100 --n 20 \
  --extra=--concurrency_limit=4
```

`--api-key-env` is a variable name, not the secret. The adapter copies that
variable to the evaluator's private environment and never puts its value in the
command preview. `--model` and `--base-url` are safe to show.

Use `--dry-run` to inspect the exact subprocess command. It does not call a
model, search service, page reader, judge, or Docker. A real invocation checks
that the selected data exists before launching the evaluator.

## Environment variables

| Variable | Used by | Required |
| --- | --- | --- |
| `MODEL_API_KEY` (or the variable named by `--api-key-env`) | model SDK | every real research run |
| `AREX_MODEL_NAME` | default model | every real research run |
| `AREX_BASE_URL` | default model endpoint | when using a custom endpoint |
| `AREX_TOKENIZER_PATH` | local token counting | unified research datasets |
| `SERPER_API_KEY` | `search`, `google_scholar` | research tools |
| `JINA_API_KEY` | `visit` | private or rate-limited Jina |
| `HF_TOKEN` | Hugging Face downloader | HLE and GAIA preparation |
| `MLE_BENCH` | MLE-bench Lite | MLE prepare/run |

Optional endpoint variables are `SERPER_API_URL`,
`SERPER_SCHOLAR_API_URL`, and `JINA_API_URL`. Keep real values in the local
ignored `.env` or a secret manager.

## Data paths

Downloadable datasets use `data/<dataset>/...`:

| Dataset | Default input |
| --- | --- |
| BrowseComp | `data/BrowseComp/browse_comp_test_set.csv` |
| DeepSearch-QA | `data/DeepSearch-QA/DSQA-full.csv` |
| HLE | `data/HLE/text_items.jsonl` |
| GAIA-2023-validation-text-103 | `data/GAIA-2023-validation-text-103/standardized_data.jsonl` |

When no `--data-root` is supplied, a matching legacy file under
`vendor/research/` is still accepted. Other evaluator datasets use the path
in `vendor/research/dataset_configs/*/config.json`; inspect them with
`python3 -m arex_v2 download --list`.

`--data-path` is rejected for a multi-dataset command rather than applying one
file to every dataset.

## Advanced options and reruns

The underlying evaluator accepts options such as:

```bash
python3 evaluate.py HLE --n 20 \
  --extra=--hle-max-completion-tokens=32768 \
  --extra=--disable-visit-fallback
```

Use `python3 vendor/research/eval_unified.py --help` for the full list. Set a
unique `--save-path` for each model, mode, and task range. Existing correct
cases are skipped by default; pass
`--extra=--skip-existing-mode=none` to rerun them deliberately.
