#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/share/project/chaofan/code/self_evolving_v15}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
UNIFY_EVAL_ROOT="${UNIFY_EVAL_ROOT:-${WORKSPACE_ROOT}/inference/code/unify_eval_0917}"
EVAL_SCRIPT="${EVAL_SCRIPT:-${UNIFY_EVAL_ROOT}/eval_unified.py}"
EVAL_PYTHON="${EVAL_PYTHON:-/share/project/chaofan/envs/browse/bin/python}"
TOKENIZER_PATH="${TOKENIZER_PATH:-/share/project/shared_models/Qwen3.8-27B}"
MODEL_NAME="Qwen3.8-27B-Stage4-Frontier-v2-10ep-ckpt92-MLE-ckpt130-Deep-Research-TIES-D070-Equal"
INFERENCE_BASE_URL="${INFERENCE_BASE_URL:-http://172.25.99.152:38754/v1}"
INFERENCE_API_KEY="${INFERENCE_API_KEY:-inspectai}"
RESULT_ROOT="${RESULT_ROOT:-${WORKSPACE_ROOT}/inference/result/0919_refine_equal/${MODEL_NAME}/browsecomp}"
BC_SAVE_PATH="${BC_SAVE_PATH:-${RESULT_ROOT}/browsecomp_all_conf95_outer10_total1500}"
OUTER1_SOURCE_ROOT="${OUTER1_SOURCE_ROOT:-${RESULT_ROOT}/browsecomp_outer1_reuse_556}"
OLD_266_SOURCE="${OLD_266_SOURCE:-${WORKSPACE_ROOT}/inference/result/0916_refine/${MODEL_NAME}/browsecomp_shuffle_1000_1266_outer1_source}"
OLD_0_300_SOURCE="${OLD_0_300_SOURCE:-${WORKSPACE_ROOT}/inference/result/0916_refine_0_300/${MODEL_NAME}/browsecomp_shuffle_0_300_tiered_outer5}"
BROWSECOMP_CONCURRENCY_LIMIT="${BROWSECOMP_CONCURRENCY_LIMIT:-60}"
CONCURRENCY_CONTROL_FILE="${CONCURRENCY_CONTROL_FILE:-${RESULT_ROOT}/concurrency.txt}"
BROWSECOMP_NUM_SAMPLES="${BROWSECOMP_NUM_SAMPLES:-1266}"
EXPECTED_REUSABLE="${EXPECTED_REUSABLE:-556}"
CONFIDENCE_THRESHOLD="${CONFIDENCE_THRESHOLD:-95}"
MIDDLE_CONFIDENCE_THRESHOLD="${MIDDLE_CONFIDENCE_THRESHOLD:-90}"
MAX_OUTER_ROUNDS="${MAX_OUTER_ROUNDS:-10}"
MAX_LLM_CALLS_PER_OUTER="${MAX_LLM_CALLS_PER_OUTER:-300}"
MAX_TOTAL_LLM_CALLS="${MAX_TOTAL_LLM_CALLS:-1500}"
SKIP_EXISTING_MODE="${SKIP_EXISTING_MODE:-all}"
JUDGE_BASE_URL="${JUDGE_BASE_URL:-http://172.24.41.25:38890/v1}"
JUDGE_API_KEY="${JUDGE_API_KEY:-dummy}"
JUDGE_MODEL="${JUDGE_MODEL:-Qwen3.5-122B-A10B}"
DRY_RUN=0

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
for arg in "$@"; do
  case "${arg}" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      printf 'Usage: bash %s [--dry-run]\n' "${BASH_SOURCE[0]}"
      printf 'Run all 1266 BrowseComp cases for the Equal model.\n'
      exit 0 ;;
    *) die "unknown argument: ${arg}" ;;
  esac
done

[[ -x "${EVAL_PYTHON}" ]] || die "Python not found: ${EVAL_PYTHON}"
[[ -f "${EVAL_SCRIPT}" ]] || die "evaluation script not found: ${EVAL_SCRIPT}"
[[ -f "${TOKENIZER_PATH}/tokenizer_config.json" ]] || die "tokenizer not found: ${TOKENIZER_PATH}"
[[ -d "${OLD_266_SOURCE}/BrowseComp" ]] || die "old BrowseComp-266 source not found"
[[ -d "${OLD_0_300_SOURCE}/BrowseComp" ]] || die "old BrowseComp [0,300) source not found"
[[ "${BROWSECOMP_NUM_SAMPLES}" =~ ^[1-9][0-9]*$ ]] || die "invalid BROWSECOMP_NUM_SAMPLES"
[[ "${EXPECTED_REUSABLE}" =~ ^[1-9][0-9]*$ ]] || die "invalid EXPECTED_REUSABLE"
[[ "${MAX_OUTER_ROUNDS}" =~ ^[1-9][0-9]*$ ]] || die "invalid MAX_OUTER_ROUNDS"
[[ "${MAX_LLM_CALLS_PER_OUTER}" =~ ^[1-9][0-9]*$ ]] || die "invalid MAX_LLM_CALLS_PER_OUTER"
[[ "${MAX_TOTAL_LLM_CALLS}" =~ ^[1-9][0-9]*$ ]] || die "invalid MAX_TOTAL_LLM_CALLS"
case "${SKIP_EXISTING_MODE}" in all|correct|none) ;; *) die "invalid SKIP_EXISTING_MODE" ;; esac

prepare_cmd=(
  "${EVAL_PYTHON}" "${SCRIPT_DIR}/prepare_browsecomp_reuse.py"
  --source "old_266=${OLD_266_SOURCE}"
  --source "old_0_300=${OLD_0_300_SOURCE}"
  --destination "${OUTER1_SOURCE_ROOT}"
  --expected-reusable "${EXPECTED_REUSABLE}"
  --dataset-size "${BROWSECOMP_NUM_SAMPLES}"
)

TOOL_PROXY_URL="${TOOL_PROXY_URL-http://10.6.212.42:2080}"
export HTTP_PROXY="${TOOL_PROXY_URL}" HTTPS_PROXY="${TOOL_PROXY_URL}" ALL_PROXY=""
export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy=""
api_hosts="$("${EVAL_PYTHON}" -c 'import sys; from urllib.parse import urlsplit; print(",".join(urlsplit(url).hostname or "" for url in sys.argv[1:]))' "${INFERENCE_BASE_URL}" "${JUDGE_BASE_URL}")"
export NO_PROXY="127.0.0.1,localhost,0.0.0.0,::1,${api_hosts}${NO_PROXY:+,${NO_PROXY}}"
export no_proxy="${NO_PROXY}"
export ENABLE_VISIT_FALLBACK=1 PYTHONUNBUFFERED=1

bc_cmd=(
  "${EVAL_PYTHON}" -u "${EVAL_SCRIPT}"
  --datasets BrowseComp --mode refine_summary
  --sdk_base_url "${INFERENCE_BASE_URL}" --sdk_api_key "${INFERENCE_API_KEY}"
  --model "${MODEL_NAME}" --save_path "${BC_SAVE_PATH}"
  --tokenizer_path "${TOKENIZER_PATH}" --sum_tokenizer_path "${TOKENIZER_PATH}"
  --summary_base_url "${INFERENCE_BASE_URL}" --summary_api_key "${INFERENCE_API_KEY}"
  --summary_model "${MODEL_NAME}"
  --judge_base_url "${JUDGE_BASE_URL}" --judge_api_key "${JUDGE_API_KEY}"
  --judge_model "${JUDGE_MODEL}" --judge-mode offical
  --dataset_start_indices BrowseComp=0
  --dataset_end_indices "BrowseComp=${BROWSECOMP_NUM_SAMPLES}"
  --dataset_shuffle BrowseComp=1 --no-shuffle
  --concurrency_limit "${BROWSECOMP_CONCURRENCY_LIMIT}"
  --concurrency-control-file "${CONCURRENCY_CONTROL_FILE}"
  --skip-existing-mode "${SKIP_EXISTING_MODE}"
  --enable-thinking --preserve_thinking --summary-enable-thinking --enable-visit-fallback
  --max_tokens 240000 --max_response_tokens 16384
  --agent_temperature 1.0 --agent_top_p 0.95 --agent_top_k 20 --agent_min_p 0.0
  --agent_presence_penalty 1.5 --agent_repetition_penalty 1.0
  --refine_summary_max_outer_rounds "${MAX_OUTER_ROUNDS}"
  --refine_summary_max_llm_calls "${MAX_LLM_CALLS_PER_OUTER}"
  --refine_summary_max_total_llm_calls "${MAX_TOTAL_LLM_CALLS}"
  --refine_summary_trigger_tokens 128000 --refine_summary_max_updates 24
  --enable_confidence_outer_retry
  --confidence_outer_retry_threshold "${CONFIDENCE_THRESHOLD}"
  --confidence_outer_retry_review_max_tokens 4096
  --enable_confidence_tiered_review
  --confidence_tiered_review_middle_threshold "${MIDDLE_CONFIDENCE_THRESHOLD}"
  --confidence_outer_resume_root "${OUTER1_SOURCE_ROOT}"
  --confidence_outer_resume_missing_from_scratch
  --general_max_attempts 10 --max_attempts 1 --case_timeout_seconds 86400
  --tool_call_regen_max_retries 20 --llm_call_max_retries 5
)

printf 'BrowseComp full run: model=%s cases=%s reusable=%s concurrency=%s\n' \
  "${MODEL_NAME}" "${BROWSECOMP_NUM_SAMPLES}" "${EXPECTED_REUSABLE}" \
  "${BROWSECOMP_CONCURRENCY_LIMIT}"
printf 'Budget: per_outer=%s max_outer=%s total=%s confidence_stop=%s\n' \
  "${MAX_LLM_CALLS_PER_OUTER}" "${MAX_OUTER_ROUNDS}" "${MAX_TOTAL_LLM_CALLS}" \
  "${CONFIDENCE_THRESHOLD}"

if (( DRY_RUN == 1 )); then
  dry_outer1_root="$(mktemp -d "${TMPDIR:-/tmp}/0919_refine_equal_bc_dryrun.XXXXXX")"
  trap 'rm -rf -- "${dry_outer1_root}"' EXIT
  rmdir "${dry_outer1_root}"
  "${prepare_cmd[@]}" --destination "${dry_outer1_root}"
  dry_bc_cmd=("${bc_cmd[@]}")
  for index in "${!dry_bc_cmd[@]}"; do
    if [[ "${dry_bc_cmd[index]}" == "${OUTER1_SOURCE_ROOT}" ]]; then
      dry_bc_cmd[index]="${dry_outer1_root}"
    fi
  done
  "${dry_bc_cmd[@]}" --dry-run
  exit 0
fi

command -v flock >/dev/null || die "flock is required"
mkdir -p "${RESULT_ROOT}/logs" "${RESULT_ROOT}/code_snapshot"
exec 9>"${RESULT_ROOT}/run.lock"
flock -n 9 || die "BrowseComp evaluation is already running"
if [[ ! -e "${CONCURRENCY_CONTROL_FILE}" ]]; then
  mkdir -p -- "$(dirname -- "${CONCURRENCY_CONTROL_FILE}")"
  printf '%s\n' "${BROWSECOMP_CONCURRENCY_LIMIT}" > "${CONCURRENCY_CONTROL_FILE}"
fi
printf 'Live concurrency file: %s (existing file takes precedence)\n' "${CONCURRENCY_CONTROL_FILE}"
"${prepare_cmd[@]}"

source_count="$("${EVAL_PYTHON}" -c 'import json,sys; print(json.load(open(sys.argv[1]))["reused_cases"])' "${OUTER1_SOURCE_ROOT}/reuse_manifest.json")"
[[ "${source_count}" -eq "${EXPECTED_REUSABLE}" ]] || \
  die "expected ${EXPECTED_REUSABLE} reusable BrowseComp cases, found ${source_count}"

export MODEL_NAME INFERENCE_BASE_URL RESULT_ROOT BC_SAVE_PATH OUTER1_SOURCE_ROOT
export OLD_266_SOURCE OLD_0_300_SOURCE BROWSECOMP_NUM_SAMPLES EXPECTED_REUSABLE
export BROWSECOMP_CONCURRENCY_LIMIT CONFIDENCE_THRESHOLD MIDDLE_CONFIDENCE_THRESHOLD
export MAX_OUTER_ROUNDS MAX_LLM_CALLS_PER_OUTER MAX_TOTAL_LLM_CALLS
export JUDGE_BASE_URL JUDGE_MODEL UNIFY_EVAL_ROOT
"${EVAL_PYTHON}" - "${RESULT_ROOT}/run_config.json" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

config = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "model": os.environ["MODEL_NAME"],
    "base_url": os.environ["INFERENCE_BASE_URL"],
    "code_root": os.environ["UNIFY_EVAL_ROOT"],
    "dataset": "BrowseComp",
    "dataset_size": int(os.environ["BROWSECOMP_NUM_SAMPLES"]),
    "num_samples": int(os.environ["BROWSECOMP_NUM_SAMPLES"]),
    "outer1_sources": [os.environ["OLD_266_SOURCE"], os.environ["OLD_0_300_SOURCE"]],
    "outer1_resume_root": os.environ["OUTER1_SOURCE_ROOT"],
    "reused_outer1_cases": int(os.environ["EXPECTED_REUSABLE"]),
    "save_path": os.environ["BC_SAVE_PATH"],
    "concurrency": int(os.environ["BROWSECOMP_CONCURRENCY_LIMIT"]),
    "max_outer": int(os.environ["MAX_OUTER_ROUNDS"]),
    "max_llm_calls_per_outer": int(os.environ["MAX_LLM_CALLS_PER_OUTER"]),
    "max_total_llm_calls": int(os.environ["MAX_TOTAL_LLM_CALLS"]),
    "confidence_threshold": float(os.environ["CONFIDENCE_THRESHOLD"]),
    "middle_review_threshold": float(os.environ["MIDDLE_CONFIDENCE_THRESHOLD"]),
    "review_strategy": "confidence_tiered",
    "reuse_policy": "same-model saved trajectories only; invalid saved errors rerun",
    "judge": {"base_url": os.environ["JUDGE_BASE_URL"], "model": os.environ["JUDGE_MODEL"]},
}
path = Path(sys.argv[1])
if path.exists():
    old = json.loads(path.read_text(encoding="utf-8"))
    old.pop("started_at", None)
    comparable = dict(config)
    comparable.pop("started_at", None)
    old.pop("concurrency", None)
    comparable.pop("concurrency", None)
    if old != comparable:
        raise SystemExit("Refusing to mix BrowseComp configurations in one result directory")
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

cp "${BASH_SOURCE[0]}" "${RESULT_ROOT}/code_snapshot/"
cp "${SCRIPT_DIR}/prepare_browsecomp_reuse.py" "${RESULT_ROOT}/code_snapshot/"
cp "${UNIFY_EVAL_ROOT}/Agent_no_subagent.py" "${RESULT_ROOT}/code_snapshot/"
cp "${UNIFY_EVAL_ROOT}/eval_unified.py" "${RESULT_ROOT}/code_snapshot/"
cp "${UNIFY_EVAL_ROOT}/live_concurrency.py" "${RESULT_ROOT}/code_snapshot/"

"${bc_cmd[@]}" 2>&1 | tee -a "${RESULT_ROOT}/logs/browsecomp_all.log"
