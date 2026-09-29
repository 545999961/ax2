# xBench-DeepSearch-2510

**Input**: CSV encrypted deep-search rows.

**Evaluation**: The unified evaluator loads `config.json`, applies the prompt in `prompt.py`, runs the model, then uses `xbench_official` as the scoring contract. xBench official grader.

**Reported metric**: official xBench score. The raw judge payload is kept in the run directory; aggregate only successful rows.

**Data**: The default path is `${AREX_DATA_ROOT}/external/xBench/DeepSearch-2510.csv` after `${AREX_DATA_ROOT}` expansion. Obtain the source CSV and pass --data-path.

**Run**:

```bash
python3 evaluate.py xBench-DeepSearch-2510 --n 10 --save-path runs/xbench-deepsearch-2510-10
```

This directory contains the prompt and judge implementation for the dataset. If the benchmark has `judge_local.py` or `judge_offical.py`, the selected judge mode is loaded from that file; otherwise the scorer metadata in `config.json` is used.
