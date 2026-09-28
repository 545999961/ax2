#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/share/project/chaofan/code/self_evolving_v15}"
EVAL_PYTHON="${EVAL_PYTHON:-/share/project/chaofan/envs/browse/bin/python}"
MODEL_NAME="${MODEL_NAME:-Qwen3.8-27B-Stage4-Frontier-v2-10ep-ckpt92-MLE-ckpt130-Deep-Research-TIES-D070-Equal}"
RESULT_BASE="${RESULT_BASE:-${WORKSPACE_ROOT}/inference/result/0919_refine_equal/${MODEL_NAME}}"
BC_RESULT_ROOT="${BC_RESULT_ROOT:-${RESULT_BASE}/browsecomp}"
BC_ROOT="${BC_ROOT:-${BC_RESULT_ROOT}/browsecomp_all_conf95_outer10_total1500/BrowseComp}"
HLE_RESULT_ROOT="${HLE_RESULT_ROOT:-${RESULT_BASE}/hle}"
HLE_OUTER1_ROOT="${HLE_OUTER1_ROOT:-${HLE_RESULT_ROOT}/hle_outer1_all/HLE}"
HLE_OUTER_ROOT="${HLE_OUTER_ROOT:-${HLE_RESULT_ROOT}/hle_all_conf95_outer10_total1500}"
BC_EXPECTED="${BC_EXPECTED:-1266}"
HLE_EXPECTED="${HLE_EXPECTED:-2158}"
MAX_OUTER="${MAX_OUTER:-10}"

lock_status() {
  local root="$1"
  if [[ ! -f "${root}/run.lock" ]]; then
    printf 'not_started'
    return
  fi
  exec 8<"${root}/run.lock"
  if flock -n -s 8; then
    printf 'not_running'
  else
    printf 'running'
  fi
  exec 8<&-
}

BC_STATUS="$(lock_status "${BC_RESULT_ROOT}")"
HLE_STATUS="$(lock_status "${HLE_RESULT_ROOT}")"

"${EVAL_PYTHON}" - \
  "${BC_ROOT}" "${BC_EXPECTED}" "${BC_STATUS}" \
  "${HLE_OUTER1_ROOT}" "${HLE_OUTER_ROOT}" "${HLE_EXPECTED}" \
  "${MAX_OUTER}" "${HLE_STATUS}" <<'PY'
import json
import re
import sys
from collections import Counter
from pathlib import Path

(
    bc_root_text,
    bc_expected_text,
    bc_status,
    hle_outer1_text,
    hle_outer_root_text,
    hle_expected_text,
    max_outer_text,
    hle_status,
) = sys.argv[1:]
bc_root = Path(bc_root_text)
bc_expected = int(bc_expected_text)
hle_outer1 = Path(hle_outer1_text)
hle_outer_root = Path(hle_outer_root_text)
hle_expected = int(hle_expected_text)
max_outer = int(max_outer_text)


def row_index(path: Path):
    match = re.search(r"_row(\d+)$", path.parent.name)
    return int(match.group(1)) if match else None


def load(root: Path):
    output = {}
    if not root.is_dir():
        return output
    for path in root.glob("*/temp.json"):
        index = row_index(path)
        if index is None:
            continue
        try:
            output[index] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return output


def score(row):
    try:
        return float(row.get("score"))
    except (TypeError, ValueError):
        return None


def confidence(row):
    value = row.get("confidence")
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip().removesuffix("%").strip()
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 100 else None


def percent(numerator, denominator):
    return f"{100 * numerator / denominator:.2f}%" if denominator else "n/a"


def print_table(columns, rows):
    text_rows = [[str(value) for value in row] for row in rows]
    widths = [
        max(len(columns[index]), *(len(row[index]) for row in text_rows))
        for index in range(len(columns))
    ]
    border = "+-" + "-+-".join("-" * width for width in widths) + "-+"

    def render(row):
        return "| " + " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(row)
        ) + " |"

    print(border)
    print(render(columns))
    print(border)
    for row in text_rows:
        print(render(row))
    print(border)


bc_rows = load(bc_root)
bc_correct = sum(score(row) == 1 for row in bc_rows.values())
bc_accepted = 0
bc_outer = Counter()
for row in bc_rows.values():
    retry = row.get("confidence_outer_retry") or {}
    accepted = retry.get("threshold_reached")
    if not isinstance(accepted, bool):
        accepted = (confidence(row) or -1) >= 95
    bc_accepted += accepted
    selected = retry.get("selected_outer_round")
    if isinstance(selected, int):
        bc_outer[selected] += 1

print(f"BrowseComp full 1266 (status: {bc_status})")
print_table(
    [
        "completed",
        "correct",
        "current_acc",
        "full_set_acc",
        "conf>=95",
        "selected_at_outer(1..10)",
    ],
    [[
        f"{len(bc_rows)}/{bc_expected}",
        bc_correct,
        percent(bc_correct, len(bc_rows)),
        percent(bc_correct, bc_expected),
        bc_accepted,
        "/".join(str(bc_outer[outer]) for outer in range(1, max_outer + 1)),
    ]],
)
print(f"Results: {bc_root}")

roots = [hle_outer1]
roots.extend(hle_outer_root / f"outer{outer}" / "HLE" for outer in range(2, max_outer + 1))
latest = {}
latest_outer = {}
for outer, root in enumerate(roots, 1):
    rows = load(root)
    for index, row in rows.items():
        latest[index] = row
        latest_outer[index] = outer

latest_correct = sum(score(row) == 1 for row in latest.values())
latest_accepted = sum((confidence(row) or -1) >= 95 for row in latest.values())
outer_positions = Counter(latest_outer.values())

print()
print(f"HLE text full 2158 (status: {hle_status})")
print("Latest available result per case:")
print_table(
    [
        "completed",
        "correct",
        "current_acc",
        "full_set_acc",
        "conf>=95",
        "latest_at_outer(1..10)",
    ],
    [[
        f"{len(latest)}/{hle_expected}",
        latest_correct,
        percent(latest_correct, len(latest)),
        percent(latest_correct, hle_expected),
        latest_accepted,
        "/".join(str(outer_positions[outer]) for outer in range(1, max_outer + 1)),
    ]],
)
print(f"Outer1 results: {hle_outer1}")
print(f"Outer2+ results: {hle_outer_root}")
PY

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"${EVAL_PYTHON}" "${SCRIPT_DIR}/status_gaia_xbench.py" "${RESULT_BASE}"
