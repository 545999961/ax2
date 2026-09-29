# DeepResearch-Bench

**Input**: JSONL query rows plus criteria and reference JSONL.

**Evaluation**: The unified evaluator loads `config.json`, applies the prompt in `prompt.py`, runs the model, then uses `deepresearch_race_official` as the scoring contract. RACE rubric over the generated long report.

**Reported metric**: RACE score. The raw judge payload is kept in the run directory; aggregate only successful rows.

**Data**: The default path is `${AREX_DATA_ROOT}/external/DeepResearch-Bench/prompt_data/query.jsonl` after `${AREX_DATA_ROOT}` expansion. Obtain upstream files and pass --data-path.

**Run**:

```bash
python3 evaluate.py DeepResearch-Bench --n 10 --save-path runs/deepresearch-bench-10
```

This directory contains the prompt and judge implementation for the dataset. If the benchmark has `judge_local.py` or `judge_offical.py`, the selected judge mode is loaded from that file; otherwise the scorer metadata in `config.json` is used.
