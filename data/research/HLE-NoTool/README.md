# HLE-NoTool

**Input**: HLE parquet rows without tool calls.

**Evaluation**: The unified evaluator loads `config.json`, applies the prompt in `prompt.py`, runs the model, then uses `hle_official` as the scoring contract. HLE official result judge.

**Reported metric**: HLE score. The raw judge payload is kept in the run directory; aggregate only successful rows.

**Data**: The default path is `${AREX_DATA_ROOT}/external/HLE/data/test-00000-of-00001.parquet` after `${AREX_DATA_ROOT}` expansion. Obtain the HLE parquet and pass --data-path.

**Run**:

```bash
python3 evaluate.py HLE-NoTool --n 10 --save-path runs/hle-notool-10
```

This directory contains the prompt and judge implementation for the dataset. If the benchmark has `judge_local.py` or `judge_offical.py`, the selected judge mode is loaded from that file; otherwise the scorer metadata in `config.json` is used.
