# BrowseComp-Zh-official-en-prompt

**Input**: JSON question rows.

**Evaluation**: The unified evaluator loads `config.json`, applies the prompt in `prompt.py`, runs the model, then uses `browsecomp_zh_official` as the scoring contract. BrowseComp-ZH Chinese official prompt/judge.

**Reported metric**: official correctness score. The raw judge payload is kept in the run directory; aggregate only successful rows.

**Data**: The default path is `${AREX_DATA_ROOT}/external/BrowseComp-Zh/official/browsecomp-zh-decrypted.json` after `${AREX_DATA_ROOT}` expansion. Obtain the licensed/source JSON and pass --data-path.

**Run**:

```bash
python3 evaluate.py BrowseComp-Zh-official-en-prompt --n 10 --save-path runs/browsecomp-zh-official-en-prompt-10
```

This directory contains the prompt and judge implementation for the dataset. If the benchmark has `judge_local.py` or `judge_offical.py`, the selected judge mode is loaded from that file; otherwise the scorer metadata in `config.json` is used.
