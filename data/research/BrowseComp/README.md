# BrowseComp

**Input**: CSV encrypted question/answer rows.

**Evaluation**: The unified evaluator loads `config.json`, applies the prompt in `prompt.py`, runs the model, then uses `browsecomp_official` as the scoring contract. BrowseComp official judge after canary/decryption checks.

**Reported metric**: official correctness score. The raw judge payload is kept in the run directory; aggregate only successful rows.

**Data**: The default path is `${AREX_DATA_ROOT}/BrowseComp/browse_comp_test_set.csv` after `${AREX_DATA_ROOT}` expansion. Run `python3 evaluate.py download BrowseComp`.

**Run**:

```bash
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10
```

This directory contains the prompt and judge implementation for the dataset. If the benchmark has `judge_local.py` or `judge_offical.py`, the selected judge mode is loaded from that file; otherwise the scorer metadata in `config.json` is used.
