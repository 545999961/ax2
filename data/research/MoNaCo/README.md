# MoNaCo

**Input**: execution-trace directory.

**Evaluation**: The unified evaluator loads `config.json`, applies the prompt in `prompt.py`, runs the model, then uses `monaco_official` as the scoring contract. Monaco final-answer judge.

**Reported metric**: Monaco official score. The raw judge payload is kept in the run directory; aggregate only successful rows.

**Data**: The default path is `${AREX_DATA_ROOT}/MoNaCo/execution_traces` after `${AREX_DATA_ROOT}` expansion. Obtain trace directory and pass --data-path.

**Run**:

```bash
python3 evaluate.py MoNaCo --n 10 --save-path runs/monaco-10
```

This directory contains the prompt and judge implementation for the dataset. If the benchmark has `judge_local.py` or `judge_offical.py`, the selected judge mode is loaded from that file; otherwise the scorer metadata in `config.json` is used.
