#!/usr/bin/env bash
set -euo pipefail

: "${DATASET_KEY:?Use a dataset runner}"
: "${DATASET_NAME:?dataset name required}"
: "${DATASET_SIZE:?dataset size required}"
DATASET_SHUFFLE="${DATASET_SHUFFLE:-0}"
EXPECTED_REUSABLE="${EXPECTED_REUSABLE:-${DATASET_SIZE}}"

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/share/project/chaofan/code/self_evolving_v15}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
UNIFY_EVAL_ROOT="${UNIFY_EVAL_ROOT:-${WORKSPACE_ROOT}/inference/code/unify_eval_0917}"
EVAL_SCRIPT="${EVAL_SCRIPT:-${UNIFY_EVAL_ROOT}/eval_unified.py}"
EVAL_PYTHON="${EVAL_PYTHON:-/share/project/chaofan/envs/browse/bin/python}"
TOKENIZER_PATH="${TOKENIZER_PATH:-/share/project/shared_models/Qwen3.8-27B}"
MODEL_NAME="Qwen3.8-27B-Stage4-Frontier-v2-10ep-ckpt92-MLE-ckpt130-Deep-Research-TIES-D070-Equal"
INFERENCE_BASE_URL="${INFERENCE_BASE_URL:-http://127.0.0.1:38754/v1}"
INFERENCE_API_KEY="${INFERENCE_API_KEY:-inspectai}"
RESULT_ROOT="${RESULT_ROOT:-${WORKSPACE_ROOT}/inference/result/0919_refine_equal/${MODEL_NAME}/${DATASET_KEY}}"
SAVE_PATH="${SAVE_PATH:-${RESULT_ROOT}/${DATASET_KEY}_all_conf95_outer10_total1500}"
REUSE_RUN_ROOT="${REUSE_RUN_ROOT:-${WORKSPACE_ROOT}/inference/result/0916_gaia_xbench_dsqa_refine_outer5/${MODEL_NAME}}"
case "${DATASET_KEY}" in
  gaia) REUSE_SUBDIR=gaia_validation_text_103_refine_outer5 ;;
  xbench) REUSE_SUBDIR=xbench_deepsearch_100_refine_outer5 ;;
  deepsearchqa) REUSE_SUBDIR=deepsearch_qa_shuffle_100_refine_outer5 ;;
  *) printf 'Unsupported dataset: %s\n' "${DATASET_KEY}" >&2; exit 1 ;;
esac
OUTER1_SOURCE_ROOT="${OUTER1_SOURCE_ROOT:-${REUSE_RUN_ROOT}/${REUSE_SUBDIR}}"
CONCURRENCY_LIMIT="${CONCURRENCY_LIMIT:-50}"
CONCURRENCY_CONTROL_FILE="${CONCURRENCY_CONTROL_FILE:-${RESULT_ROOT}/concurrency.txt}"
NUM_SAMPLES="${NUM_SAMPLES:-${DATASET_SIZE}}"
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
      printf 'Run %s cases for %s with the Equal model.\n' "${NUM_SAMPLES}" "${DATASET_NAME}"
      exit 0 ;;
    *) die "unknown argument: ${arg}" ;;
  esac
done

[[ -x "${EVAL_PYTHON}" ]] || die "Python not found: ${EVAL_PYTHON}"
[[ -f "${EVAL_SCRIPT}" ]] || die "evaluation script not found: ${EVAL_SCRIPT}"
[[ -f "${TOKENIZER_PATH}/tokenizer_config.json" ]] || die "tokenizer not found: ${TOKENIZER_PATH}"
[[ "${NUM_SAMPLES}" =~ ^[1-9][0-9]*$ ]] || die "invalid NUM_SAMPLES"
[[ "${MAX_OUTER_ROUNDS}" =~ ^[1-9][0-9]*$ ]] || die "invalid MAX_OUTER_ROUNDS"
[[ "${MAX_LLM_CALLS_PER_OUTER}" =~ ^[1-9][0-9]*$ ]] || die "invalid MAX_LLM_CALLS_PER_OUTER"
[[ "${MAX_TOTAL_LLM_CALLS}" =~ ^[1-9][0-9]*$ ]] || die "invalid MAX_TOTAL_LLM_CALLS"
[[ "${CONCURRENCY_LIMIT}" =~ ^[1-9][0-9]*$ ]] || die "invalid CONCURRENCY_LIMIT"
[[ "${NUM_SAMPLES}" -le "${DATASET_SIZE}" ]] || die "NUM_SAMPLES exceeds dataset size"
case "${SKIP_EXISTING_MODE}" in all|correct|none) ;; *) die "invalid SKIP_EXISTING_MODE" ;; esac

"${EVAL_PYTHON}" "${SCRIPT_DIR}/validate_gaia_xbench_reuse.py" \
  --code-root "${UNIFY_EVAL_ROOT}" --source "${OUTER1_SOURCE_ROOT}" \
  --dataset "${DATASET_NAME}" --model "${MODEL_NAME}" --dataset-size "${DATASET_SIZE}" \
  --shuffle "${DATASET_SHUFFLE}" --expected-reusable "${EXPECTED_REUSABLE}"

TOOL_PROXY_URL="${TOOL_PROXY_URL-http://10.6.212.42:2080}"
export HTTP_PROXY="${TOOL_PROXY_URL}" HTTPS_PROXY="${TOOL_PROXY_URL}" ALL_PROXY=""
export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy=""
api_hosts="$("${EVAL_PYTHON}" -c 'import sys; from urllib.parse import urlsplit; print(",".join(urlsplit(url).hostname or "" for url in sys.argv[1:]))' "${INFERENCE_BASE_URL}" "${JUDGE_BASE_URL}")"
export NO_PROXY="127.0.0.1,localhost,0.0.0.0,::1,${api_hosts}${NO_PROXY:+,${NO_PROXY}}"
export no_proxy="${NO_PROXY}"
export ENABLE_VISIT_FALLBACK=1 PYTHONUNBUFFERED=1

eval_cmd=(
  "${EVAL_PYTHON}" -u "${EVAL_SCRIPT}"
  --datasets "${DATASET_NAME}" --mode refine_summary
  --sdk_base_url "${INFERENCE_BASE_URL}" --sdk_api_key "${INFERENCE_API_KEY}"
  --model "${MODEL_NAME}" --save_path "${SAVE_PATH}"
  --tokenizer_path "${TOKENIZER_PATH}" --sum_tokenizer_path "${TOKENIZER_PATH}"
  --summary_base_url "${INFERENCE_BASE_URL}" --summary_api_key "${INFERENCE_API_KEY}"
  --summary_model "${MODEL_NAME}"
  --judge_base_url "${JUDGE_BASE_URL}" --judge_api_key "${JUDGE_API_KEY}"
  --judge_model "${JUDGE_MODEL}" --judge-mode offical
  --dataset_start_indices "${DATASET_NAME}=0"
  --dataset_end_indices "${DATASET_NAME}=${NUM_SAMPLES}"
  --dataset_shuffle "${DATASET_NAME}=${DATASET_SHUFFLE}" --no-shuffle
  --concurrency_limit "${CONCURRENCY_LIMIT}"
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
  --general_max_attempts 10 --max_attempts 1 --case_timeout_seconds 86400
  --tool_call_regen_max_retries 20 --llm_call_max_retries 5
)

if [[ "${EXPECTED_REUSABLE}" -lt "${DATASET_SIZE}" ]]; then
  eval_cmd+=(--confidence_outer_resume_missing_from_scratch)
fi

printf 'Dataset: %s; cases=%s; concurrency=%s; outer=%s; total_calls=%s\n' \
  "${DATASET_NAME}" "${NUM_SAMPLES}" "${CONCURRENCY_LIMIT}" "${MAX_OUTER_ROUNDS}" "${MAX_TOTAL_LLM_CALLS}"
if (( DRY_RUN == 1 )); then
  "${eval_cmd[@]}" --dry-run
  exit 0
fi

command -v flock >/dev/null || die "flock is required"
mkdir -p "${RESULT_ROOT}/logs" "${RESULT_ROOT}/code_snapshot"
exec 9>"${RESULT_ROOT}/run.lock"
flock -n 9 || die "${DATASET_NAME} evaluation is already running"
if [[ ! -e "${CONCURRENCY_CONTROL_FILE}" ]]; then
  mkdir -p -- "$(dirname -- "${CONCURRENCY_CONTROL_FILE}")"
  printf '%s\n' "${CONCURRENCY_LIMIT}" > "${CONCURRENCY_CONTROL_FILE}"
fi
printf 'Live concurrency file: %s (existing file takes precedence)\n' "${CONCURRENCY_CONTROL_FILE}"
export MODEL_NAME INFERENCE_BASE_URL RESULT_ROOT SAVE_PATH DATASET_NAME NUM_SAMPLES
export CONCURRENCY_CONTROL_FILE DATASET_SIZE
export OUTER1_SOURCE_ROOT
export DATASET_SHUFFLE
export EXPECTED_REUSABLE
export CONCURRENCY_LIMIT CONFIDENCE_THRESHOLD MIDDLE_CONFIDENCE_THRESHOLD
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
    "dataset": os.environ["DATASET_NAME"],
    "dataset_size": int(os.environ["DATASET_SIZE"]),
    "num_samples": int(os.environ["NUM_SAMPLES"]),
    "save_path": os.environ["SAVE_PATH"],
    "concurrency": int(os.environ["CONCURRENCY_LIMIT"]),
    "concurrency_control_file": os.environ["CONCURRENCY_CONTROL_FILE"],
    "max_outer": int(os.environ["MAX_OUTER_ROUNDS"]),
    "max_llm_calls_per_outer": int(os.environ["MAX_LLM_CALLS_PER_OUTER"]),
    "max_total_llm_calls": int(os.environ["MAX_TOTAL_LLM_CALLS"]),
    "confidence_threshold": float(os.environ["CONFIDENCE_THRESHOLD"]),
    "middle_review_threshold": float(os.environ["MIDDLE_CONFIDENCE_THRESHOLD"]),
    "review_strategy": "confidence_tiered",
    "outer1_resume_root": os.environ["OUTER1_SOURCE_ROOT"],
    "reused_outer1_cases": min(int(os.environ["NUM_SAMPLES"]), int(os.environ["EXPECTED_REUSABLE"])),
    "reuse_policy": "recover outer1 only from same-model saved refine_summary trajectories",
    "judge": {"base_url": os.environ["JUDGE_BASE_URL"], "model": os.environ["JUDGE_MODEL"]},
}
if int(os.environ["EXPECTED_REUSABLE"]) < int(os.environ["DATASET_SIZE"]):
    config["missing_outer1_from_scratch"] = True
    config["fresh_outer1_cases"] = config["num_samples"] - config["reused_outer1_cases"]
if os.environ["DATASET_SHUFFLE"] == "1":
    config.update(shuffle=True, seed=66)
path = Path(sys.argv[1])
if path.exists():
    old = json.loads(path.read_text(encoding="utf-8"))
    old.pop("started_at", None)
    comparable = dict(config)
    comparable.pop("started_at", None)
    old.pop("concurrency", None)
    comparable.pop("concurrency", None)
    if old != comparable:
        raise SystemExit("Refusing to mix evaluation configurations in one result directory")
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

cp "${BASH_SOURCE[0]}" "${RESULT_ROOT}/code_snapshot/"
cp "${SCRIPT_DIR}/run_${DATASET_KEY}_all.sh" "${RESULT_ROOT}/code_snapshot/"
cp "${SCRIPT_DIR}/validate_gaia_xbench_reuse.py" "${RESULT_ROOT}/code_snapshot/"
cp "${UNIFY_EVAL_ROOT}/Agent_no_subagent.py" "${RESULT_ROOT}/code_snapshot/"
cp "${UNIFY_EVAL_ROOT}/eval_unified.py" "${RESULT_ROOT}/code_snapshot/"
cp "${UNIFY_EVAL_ROOT}/live_concurrency.py" "${RESULT_ROOT}/code_snapshot/"

"${eval_cmd[@]}" 2>&1 | tee -a "${RESULT_ROOT}/logs/${DATASET_KEY}_all.log"
