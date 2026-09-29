# Source tree

`evaluation/arex_v2` is the maintained repository boundary. It resolves a dataset,
checks its input, and delegates to one of the three backends.

The remaining directories are pinned evaluator snapshots or runtime adapters:

- `research_eval/` — unified research evaluator and its HLE support code.
- `frontier_cs/` — Frontier-CS Python evaluator.
- `algorithmic/` — the local Docker/SkyPilot judge service.
- `mle_lite/` — MLE-bench Lite runner and host grader.
- `harbor_pi_supported/`, `frontier_configs/`, `frontier_run/` — upstream support
  files used by the Frontier/Harbor experiments.

Dataset definitions are intentionally outside this tree in `data/`. This
keeps prompt and judge changes reviewable without searching through a runner
snapshot.
