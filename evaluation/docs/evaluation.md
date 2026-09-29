# Evaluation and scoring

Select a dataset at the repository boundary and let the wrapper choose its
bundled evaluator:

```bash
python3 evaluate.py list
python3 evaluate.py BrowseComp --n 1 --dry-run
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10
```

`--start-index I --n N` evaluates rows in `[I, I+N)`. The wrapper uses one
result directory per selected dataset. It checks prepared paths before starting
a real run; dry-run only prints the constructed subprocess command.

## Research datasets

Every case writes a `result.json`. Read `status`, `official_scorer`,
`judge_raw`, and error fields before aggregating `score_result.score`.
Missing credentials or missing data are configuration errors and should not be
counted as model failures.

| Dataset | Input and scorer |
| --- | --- |
| BrowseComp | Encrypted CSV; BrowseComp official judge |
| DeepSearch-QA | CSV; official Gemini-autorater style scorer |
| HLE | Text-only HLE JSONL; 0724 HLE judge, with `metrics.full_credit` |
| GAIA-2023-validation-text-103 | Text-only GAIA JSONL; WebAgent-style text judge |
| xBench-DeepSearch-2510 | Encrypted CSV; xBench official judge |
| HLE-NoTool | HLE parquet; HLE judge |
| WideSearch-en / WideSearch-zh-en-prompt | WideSearch JSONL; official table score |
| WideSearch-en-sft-eval / WideSearch-zh-sft-eval | SFT split of the same table score |
| DeepWideSearch | DeepWideSearch JSONL; official table score |
| MoNaCo | Execution traces; Monaco score |
| DeepResearch-Bench | Query and criteria files; RACE score |
| BrowseComp-Zh-official-en-prompt | BrowseComp-ZH judge |

The four datasets with a repository download recipe are prepared with:

```bash
python3 evaluate.py download BrowseComp
python3 evaluate.py download DeepSearch-QA
python3 evaluate.py download HLE                 # requires HF_TOKEN and access
python3 evaluate.py download GAIA-2023-validation-text-103  # requires HF_TOKEN
python3 evaluate.py download --list
```

The other datasets remain available through the same evaluator, but their
source files must be obtained according to their upstream license and placed at
the configured path. Use `--data-path` for a single dataset or inspect the
paths with `download --list`.

## Frontier-CS algorithmic

Download the public problem archive and evaluate a C++17 solution:

```bash
python3 scripts/download_data.py --dataset algorithmic
python3 evaluate.py algorithmic 1 path/to/solution.cpp --backend docker
```

The checker reports case scores such as `scoreRatio` and
`scoreRatioUnbounded`. Keep the complete checker and Docker log with the
result. A solution passes only when all required cases pass.

## MLE-bench Lite

Prepare and run one competition, then use the host grader:

```bash
MLE_BENCH=$HOME/mle-bench python3 evaluate.py mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 evaluate.py mle leaf-classification
MLE_BENCH=$HOME/mle-bench \
  bash evaluation/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
```

Use `score`, `valid_submission`, and medal/threshold fields from
`grade.log` as the final metric. Container `/validate` output is diagnostic.

## Reproducibility

Record the Git commit, model, base URL, task range, mode, evaluator extras, and
data checksum beside each result root. Never record API key values. Upstream
commits and licenses are listed in `SNAPSHOT.txt` and
`THIRD_PARTY_NOTICES.md`.
