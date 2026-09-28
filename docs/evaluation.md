# Evaluation and scoring

Use the dataset name and `--n` to define the selection. The wrapper converts
`--start-index I --n N` into the evaluator range `[I, I+N)`.

## Research datasets

Each selected case writes a `result.json`. Aggregate
`score_result.score` only after checking `status`, `official_scorer`, `judge_raw`,
and any `error_type` or truncation fields.

| Dataset | Input | Scoring signal |
| --- | --- | --- |
| BrowseComp | encrypted `browse_comp_test_set.csv` | BrowseComp official judge; use `score_result.score` per case and report accuracy |
| HLE | `text_items.jsonl` plus attachments | 0724 HLE judge; `score_result.metrics.full_credit` identifies full credit |
| GAIA-2023-validation-text-103 | text JSONL plus referenced files | WebAgent-style LLM judge; average case scores and report leak-filtered cases |
| DeepSearch-QA | `DSQA-full.csv` | official Gemini-autorater-style scorer; inspect parse failures separately |

Research tools are fixed by the harness: `search` and `google_scholar` call
Serper, while `visit` calls Jina Reader. A missing credential is a configuration
error, not a model failure.

The registry also exposes the following datasets. They use the same per-case
`result.json` contract; the named upstream scorer is recorded in
`official_scorer` and its numeric output is under `score_result`.

| Dataset | Evaluator signal |
| --- | --- |
| xBench-DeepSearch-2510 | xBench official grader score |
| HLE-NoTool | HLE judge score and `metrics.full_credit` |
| WideSearch-en / WideSearch-zh-en-prompt | WideSearch official table score |
| WideSearch-en-sft-eval / WideSearch-zh-sft-eval | same WideSearch score on the SFT split |
| DeepWideSearch | DeepWideSearch official table score |
| MoNaCo | Monaco execution-trace score |
| DeepResearch-Bench | DeepResearch-Bench RACE score |
| BrowseComp-Zh-official-en-prompt | BrowseComp-ZH judge score |

For a smoke test:

```bash
python3 -m arex_v2 research BrowseComp --n 1 --dry-run
python3 -m arex_v2 research BrowseComp --n 1 --save-path runs/browsecomp-smoke
```

## Frontier-CS algorithmic

```bash
python3 scripts/download_data.py --dataset algorithmic
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker
```

The judge compiles the C++17 solution, runs hidden cases, and reports checker
case scores such as `scoreRatio` and `scoreRatioUnbounded`. A solution is passed
only when the checker marks every required case as passed; retain the complete
Frontier/Docker log with the result.

## MLE-bench Lite

Prepare and run one competition at a time:

```bash
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
```

Grade the generated submission with the host grader:

```bash
MLE_BENCH=$HOME/mle-bench \
  bash vendor/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
```

Use `grade.log` fields such as `score`, `valid_submission`, and medal/threshold
status as the final metric. Container `/validate` output is diagnostic only.

## Reproducibility

Record the Git commit, model name, base URL, task range, mode, evaluator extras,
and data checksum beside each result root. Never record API key values. Keep the
upstream commit and license information in `SNAPSHOT.txt` and
`THIRD_PARTY_NOTICES.md`.
