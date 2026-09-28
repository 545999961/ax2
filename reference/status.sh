#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/share/project/chaofan/code/self_evolving_v15}"
EVAL_PYTHON="${EVAL_PYTHON:-/share/project/chaofan/envs/browse/bin/python}"
MODEL_NAME="Qwen3.8-27B-Stage4-Frontier-v2-10ep-ckpt92-MLE-ckpt130-Deep-Research-TIES-D070-Equal"
RESULT_BASE="${RESULT_BASE:-${WORKSPACE_ROOT}/inference/result/0919_refine_equal/${MODEL_NAME}}"

"${EVAL_PYTHON}" - "${RESULT_BASE}" <<'PY'
import json
import re
import sys
from collections import Counter
from pathlib import Path

base = Path(sys.argv[1])
row_re = re.compile(r"_row(\d+)$")


def rows(root: Path):
    output = {}
    if not root.is_dir():
        return output
    for path in root.glob("*/temp.json"):
        match = row_re.search(path.parent.name)
        if match is None:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        output[int(match.group(1))] = data
    return output


def rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.2f}%"


bc_root = base / "browsecomp/browsecomp_all_conf95_outer10_total1500/BrowseComp"
bc_rows = rows(bc_root)
bc_outer = Counter()
bc_correct = 0
bc_threshold = 0
for row in bc_rows.values():
    bc_correct += row.get("score") == 1
    retry = row.get("confidence_outer_retry") or {}
    bc_outer[str(retry.get("selected_outer_round"))] += 1
    bc_threshold += bool(retry.get("threshold_reached"))

print("BrowseComp")
print(f"  completed: {len(bc_rows)}/1266")
print(f"  correct: {bc_correct}")
print(f"  current accuracy: {bc_correct}/{len(bc_rows)} ({rate(bc_correct, len(bc_rows))})")
print(f"  full-set accuracy: {bc_correct}/1266 ({rate(bc_correct, 1266)})")
print(f"  confidence threshold reached: {bc_threshold}")
print(f"  selected outer: {dict(sorted(bc_outer.items()))}")

outer1 = rows(base / "hle/hle_outer1_all/HLE")
latest = {index: (1, row) for index, row in outer1.items()}
per_outer = [(1, len(outer1))]
for outer in range(2, 11):
    current = rows(base / f"hle/hle_all_conf95_outer10_total1500/outer{outer}/HLE")
    per_outer.append((outer, len(current)))
    for index, row in current.items():
        latest[index] = (outer, row)

hle_correct = sum(row.get("score") == 1 for _, row in latest.values())
hle_threshold = sum(
    isinstance(row.get("confidence"), (int, float))
    and not isinstance(row.get("confidence"), bool)
    and row["confidence"] >= 95
    for _, row in latest.values()
)
latest_outer = Counter(outer for outer, _ in latest.values())
print("HLE")
print(f"  outer1 completed: {len(outer1)}/2158")
print(f"  per outer completed: {dict(per_outer)}")
print(f"  latest completed: {len(latest)}/2158")
print(f"  latest correct: {hle_correct}")
print(f"  current accuracy: {hle_correct}/{len(latest)} ({rate(hle_correct, len(latest))})")
print(f"  full-set accuracy: {hle_correct}/2158 ({rate(hle_correct, 2158)})")
print(f"  latest confidence >=95: {hle_threshold}")
print(f"  latest at outer: {dict(sorted(latest_outer.items()))}")
PY

for dataset in browsecomp hle; do
  lock="${RESULT_BASE}/${dataset}/run.lock"
  if [[ ! -e "${lock}" ]]; then
    printf '%s process: not started\n' "${dataset}"
  elif flock -n "${lock}" true 2>/dev/null; then
    printf '%s process: stopped\n' "${dataset}"
  else
    printf '%s process: running\n' "${dataset}"
  fi
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"${EVAL_PYTHON}" "${SCRIPT_DIR}/status_gaia_xbench.py" "${RESULT_BASE}"
