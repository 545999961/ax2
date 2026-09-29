# DeepWideSearch

**Input**: JSONL research questions and table references.

**Evaluation**: The unified evaluator loads `config.json`, applies the prompt in `prompt.py`, runs the model, then uses `deepwidesearch_official` as the scoring contract. DeepWideSearch official table evaluator.

**Reported metric**: table score. The raw judge payload is kept in the run directory; aggregate only successful rows.

**Data**: The default path is `${AREX_DATA_ROOT}/external/DeepWideSearch/overall_20250916.jsonl` after `${AREX_DATA_ROOT}` expansion. Obtain upstream files and pass --data-path.

**Run**:

```bash
python3 evaluate.py DeepWideSearch --n 10 --save-path runs/deepwidesearch-10
```

This directory contains the prompt and judge implementation for the dataset. If the benchmark has `judge_local.py` or `judge_offical.py`, the selected judge mode is loaded from that file; otherwise the scorer metadata in `config.json` is used.
