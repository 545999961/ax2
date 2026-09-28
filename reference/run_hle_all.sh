#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/share/project/chaofan/code/self_evolving_v15}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
UNIFY_EVAL_ROOT="${UNIFY_EVAL_ROOT:-${WORKSPACE_ROOT}/inference/code/unify_eval_0917}"
EVAL_SCRIPT="${EVAL_SCRIPT:-${UNIFY_EVAL_ROOT}/eval_unified.py}"
EVAL_PYTHON="${EVAL_PYTHON:-/share/project/chaofan/envs/browse/bin/python}"
HLE_VENDOR_ROOT="${HLE_VENDOR_ROOT:-${UNIFY_EVAL_ROOT}/hle_0724_vendor}"
TOKENIZER_PATH="${TOKENIZER_PATH:-/share/project/shared_models/Qwen3.8-27B}"
MODEL_NAME="Qwen3.8-27B-Stage4-Frontier-v2-10ep-ckpt92-MLE-ckpt130-Deep-Research-TIES-D070-Equal"
INFERENCE_BASE_URL="${INFERENCE_BASE_URL:-http://172.25.99.152:38754/v1}"
INFERENCE_API_KEY="${INFERENCE_API_KEY:-inspectai}"
RESULT_ROOT="${RESULT_ROOT:-${WORKSPACE_ROOT}/inference/result/0919_refine_equal/${MODEL_NAME}/hle}"
OUTER1_ROOT="${OUTER1_ROOT:-${RESULT_ROOT}/hle_outer1_all}"
HLE_SAVE_ROOT="${HLE_SAVE_ROOT:-${RESULT_ROOT}/hle_all_conf95_outer10_total1500}"
CONTROLLER_ROOT="${CONTROLLER_ROOT:-${RESULT_ROOT}/controller_batches}"
HLE_200_SOURCE="${HLE_200_SOURCE:-${WORKSPACE_ROOT}/inference/result/0916_refine_hle200_improved/${MODEL_NAME}/hle_confidence_update_context_200}"
HLE_500_SOURCE="${HLE_500_SOURCE:-${WORKSPACE_ROOT}/inference/result/0916_refine_hle500_disjoint/${MODEL_NAME}/hle_fresh500_disjoint_from_seed125_200}"
CONCURRENCY_LIMIT="${CONCURRENCY_LIMIT:-50}"
HLE_NUM_SAMPLES="${HLE_NUM_SAMPLES:-2158}"
HLE_DATASET_SIZE="${HLE_DATASET_SIZE:-2158}"
EXPECTED_REUSABLE="${EXPECTED_REUSABLE:-685}"
HLE_SEED="${HLE_SEED:-125}"
HLE_MAX_STEPS="${HLE_MAX_STEPS:-300}"
MAX_TOTAL_STEPS="${MAX_TOTAL_STEPS:-1500}"
MAX_OUTER="${MAX_OUTER:-10}"
CONFIDENCE_THRESHOLD="${CONFIDENCE_THRESHOLD:-95}"
HLE_REVIEW_MIDDLE_THRESHOLD="${HLE_REVIEW_MIDDLE_THRESHOLD:-90}"
HLE_REVIEW_MAX_TOKENS="${HLE_REVIEW_MAX_TOKENS:-4096}"
JUDGE_BASE_URL="${JUDGE_BASE_URL:-http://172.24.41.25:38890/v1}"
JUDGE_API_KEY="${JUDGE_API_KEY:-dummy}"
JUDGE_MODEL="${JUDGE_MODEL:-Qwen3.5-122B-A10B}"
DRY_RUN=0
PHASE=all

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
for arg in "$@"; do
  case "${arg}" in
    --dry-run) DRY_RUN=1 ;;
    --outer1-only) PHASE=outer1 ;;
    --outer-chain-only) PHASE=chain ;;
    -h|--help)
      printf 'Usage: bash %s [--dry-run] [--outer1-only|--outer-chain-only]\n' "${BASH_SOURCE[0]}"
      printf 'Run all 2158 HLE cases for the Equal model.\n'
      exit 0 ;;
    *) die "unknown argument: ${arg}" ;;
  esac
done

[[ -x "${EVAL_PYTHON}" ]] || die "Python not found: ${EVAL_PYTHON}"
[[ -f "${EVAL_SCRIPT}" ]] || die "evaluation script not found: ${EVAL_SCRIPT}"
[[ -f "${HLE_VENDOR_ROOT}/run_evaluation_kimi_agent.py" ]] || die "HLE agent not found"
[[ -f "${HLE_VENDOR_ROOT}/HLE_judge.py" ]] || die "HLE judge not found"
[[ -f "${TOKENIZER_PATH}/tokenizer_config.json" ]] || die "tokenizer not found: ${TOKENIZER_PATH}"
for source in "${HLE_200_SOURCE}" "${HLE_500_SOURCE}"; do
  [[ -d "${source}/HLE" ]] || die "HLE reuse source not found: ${source}"
done
[[ "${HLE_NUM_SAMPLES}" =~ ^[1-9][0-9]*$ ]] || die "invalid HLE_NUM_SAMPLES"
[[ "${HLE_DATASET_SIZE}" =~ ^[1-9][0-9]*$ ]] || die "invalid HLE_DATASET_SIZE"
[[ "${EXPECTED_REUSABLE}" =~ ^[1-9][0-9]*$ ]] || die "invalid EXPECTED_REUSABLE"
[[ "${HLE_MAX_STEPS}" =~ ^[1-9][0-9]*$ ]] || die "invalid HLE_MAX_STEPS"
[[ "${MAX_TOTAL_STEPS}" =~ ^[1-9][0-9]*$ ]] || die "invalid MAX_TOTAL_STEPS"
[[ "${MAX_OUTER}" =~ ^([2-9]|[1-9][0-9]+)$ ]] || die "MAX_OUTER must be at least 2"

prepare_cmd=(
  "${EVAL_PYTHON}" "${SCRIPT_DIR}/prepare_hle_reuse.py"
  --source "hle_200=${HLE_200_SOURCE}"
  --source "hle_500=${HLE_500_SOURCE}"
  --destination "${OUTER1_ROOT}"
  --expected-reusable "${EXPECTED_REUSABLE}"
  --dataset-size "${HLE_DATASET_SIZE}"
)

TOOL_PROXY_URL="${TOOL_PROXY_URL-http://10.6.212.42:2080}"
export HTTP_PROXY="${TOOL_PROXY_URL}" HTTPS_PROXY="${TOOL_PROXY_URL}" ALL_PROXY=""
export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" all_proxy=""
api_hosts="$("${EVAL_PYTHON}" -c 'import sys; from urllib.parse import urlsplit; print(",".join(urlsplit(url).hostname or "" for url in sys.argv[1:]))' "${INFERENCE_BASE_URL}" "${JUDGE_BASE_URL}")"
export NO_PROXY="127.0.0.1,localhost,0.0.0.0,::1,${api_hosts}${NO_PROXY:+,${NO_PROXY}}"
export no_proxy="${NO_PROXY}"
export ENABLE_VISIT_FALLBACK=1 PYTHONUNBUFFERED=1

common_cmd=(
  "${EVAL_PYTHON}" -u "${EVAL_SCRIPT}"
  --datasets HLE --mode direct
  --sdk_base_url "${INFERENCE_BASE_URL}" --sdk_api_key "${INFERENCE_API_KEY}"
  --model "${MODEL_NAME}"
  --tokenizer_path "${TOKENIZER_PATH}" --sum_tokenizer_path "${TOKENIZER_PATH}"
  --enable-thinking --preserve_thinking --summary-enable-thinking
  --judge_base_url "${JUDGE_BASE_URL}" --judge_api_key "${JUDGE_API_KEY}"
  --judge_model "${JUDGE_MODEL}" --judge-mode offical
  --dataset_start_indices HLE=0 --dataset_end_indices "HLE=${HLE_DATASET_SIZE}"
  --dataset_shuffle HLE=0 --no-shuffle
  --concurrency_limit "${CONCURRENCY_LIMIT}" --skip-existing-mode all
  --hle-harness-dir "${HLE_VENDOR_ROOT}"
  --hle-judge-script "${HLE_VENDOR_ROOT}/HLE_judge.py"
  --hle-seed "${HLE_SEED}" --hle-num-samples "${HLE_NUM_SAMPLES}"
  --hle-max-completion-tokens 16384 --hle-truncation-max-completion-tokens 8192
  --hle-max-context-tokens 200000 --hle-max-total-tokens 262144
  --hle-max-steps "${HLE_MAX_STEPS}" --hle-tool-call-regen-max-retries 20
  --hle-temperature 0.9 --hle-top-p 0.93 --hle-top-k 40 --hle-min-p 0.0
  --hle-presence-penalty 0.0 --hle-repetition-penalty 1.08
  --hle-enable-thinking --hle-preserve-thinking
  --hle-review-threshold "${CONFIDENCE_THRESHOLD}"
  --hle-review-middle-threshold "${HLE_REVIEW_MIDDLE_THRESHOLD}"
  --hle-review-max-tokens "${HLE_REVIEW_MAX_TOKENS}"
  --hle-judge-num-workers 4 --hle-judge-timeout 600
  --hle-judge-max-retries 0 --hle-judge-attempts 3 --hle-judge-max-tokens 8192
  --enable-visit-fallback --max_attempts 1
)

outer1_cmd=("${common_cmd[@]}" --save_path "${OUTER1_ROOT}")
chain_cmd=(
  "${common_cmd[@]}"
  --save_path "${CONTROLLER_ROOT}"
  --hle-rerun-source-root "${OUTER1_ROOT}"
  --hle-rerun-confidence-threshold "${CONFIDENCE_THRESHOLD}"
  --hle-outer-review-resume --hle-outer-round 2
  --hle-per-case-outer-max "${MAX_OUTER}"
  --hle-per-case-outer-root "${HLE_SAVE_ROOT}"
  --hle-per-case-total-max-steps "${MAX_TOTAL_STEPS}"
)
pipeline_cmd=("${chain_cmd[@]}" --hle-per-case-fill-missing-outer1)

printf 'HLE full run: model=%s cases=%s reusable=%s concurrency=%s\n' \
  "${MODEL_NAME}" "${HLE_NUM_SAMPLES}" "${EXPECTED_REUSABLE}" "${CONCURRENCY_LIMIT}"
printf 'Budget: per_outer=%s max_outer=%s total=%s confidence_stop=%s phase=%s\n' \
  "${HLE_MAX_STEPS}" "${MAX_OUTER}" "${MAX_TOTAL_STEPS}" \
  "${CONFIDENCE_THRESHOLD}" "${PHASE}"

if (( DRY_RUN == 1 )); then
  dry_outer1_root="$(mktemp -d "${TMPDIR:-/tmp}/0919_refine_equal_hle_dryrun.XXXXXX")"
  trap 'rm -rf -- "${dry_outer1_root}"' EXIT
  rmdir "${dry_outer1_root}"
  "${prepare_cmd[@]}" --destination "${dry_outer1_root}"
  dry_outer1_cmd=("${outer1_cmd[@]}")
  dry_chain_cmd=("${chain_cmd[@]}")
  dry_pipeline_cmd=("${pipeline_cmd[@]}")
  for command_name in dry_outer1_cmd dry_chain_cmd dry_pipeline_cmd; do
    declare -n command_ref="${command_name}"
    for index in "${!command_ref[@]}"; do
      if [[ "${command_ref[index]}" == "${OUTER1_ROOT}" ]]; then
        command_ref[index]="${dry_outer1_root}"
      fi
    done
    unset -n command_ref
  done
  case "${PHASE}" in
    outer1) "${dry_outer1_cmd[@]}" --dry-run ;;
    chain) "${dry_chain_cmd[@]}" --dry-run ;;
    all) "${dry_pipeline_cmd[@]}" --dry-run ;;
  esac
  exit 0
fi

command -v flock >/dev/null || die "flock is required"
mkdir -p "${RESULT_ROOT}/logs" "${RESULT_ROOT}/code_snapshot" "${HLE_SAVE_ROOT}"
exec 9>"${RESULT_ROOT}/run.lock"
flock -n 9 || die "HLE evaluation is already running"
"${prepare_cmd[@]}"

export MODEL_NAME INFERENCE_BASE_URL RESULT_ROOT OUTER1_ROOT HLE_SAVE_ROOT
export HLE_200_SOURCE HLE_500_SOURCE EXPECTED_REUSABLE
export CONCURRENCY_LIMIT HLE_NUM_SAMPLES HLE_DATASET_SIZE HLE_SEED HLE_MAX_STEPS
export MAX_TOTAL_STEPS MAX_OUTER CONFIDENCE_THRESHOLD HLE_REVIEW_MIDDLE_THRESHOLD
export HLE_REVIEW_MAX_TOKENS JUDGE_BASE_URL JUDGE_MODEL UNIFY_EVAL_ROOT
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
    "dataset": "HLE",
    "dataset_size": int(os.environ["HLE_DATASET_SIZE"]),
    "num_samples": int(os.environ["HLE_NUM_SAMPLES"]),
    "seed": int(os.environ["HLE_SEED"]),
    "outer1_sources": [
        os.environ["HLE_200_SOURCE"],
        os.environ["HLE_500_SOURCE"],
    ],
    "outer1_root": os.environ["OUTER1_ROOT"],
    "reused_outer1_cases": int(os.environ["EXPECTED_REUSABLE"]),
    "save_root": os.environ["HLE_SAVE_ROOT"],
    "concurrency": int(os.environ["CONCURRENCY_LIMIT"]),
    "max_outer": int(os.environ["MAX_OUTER"]),
    "max_model_calls_per_outer": int(os.environ["HLE_MAX_STEPS"]),
    "max_total_model_calls": int(os.environ["MAX_TOTAL_STEPS"]),
    "confidence_threshold": float(os.environ["CONFIDENCE_THRESHOLD"]),
    "review": {
        "enabled_for_outer_transition": True,
        "prompt_version": "hle_solution_review_v1",
        "reviews_per_outer_transition": 1,
        "middle_threshold": float(os.environ["HLE_REVIEW_MIDDLE_THRESHOLD"]),
        "max_tokens": int(os.environ["HLE_REVIEW_MAX_TOKENS"]),
        "counts_toward_total_model_call_budget": True,
    },
    "reuse_policy": "reuse only valid outer1 finishes from the improved 200 and fresh disjoint 500 runs",
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
        raise SystemExit("Refusing to mix HLE configurations in one result directory")
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

cp "${BASH_SOURCE[0]}" "${RESULT_ROOT}/code_snapshot/"
cp "${SCRIPT_DIR}/prepare_hle_reuse.py" "${RESULT_ROOT}/code_snapshot/"
cp "${UNIFY_EVAL_ROOT}/eval_unified.py" "${RESULT_ROOT}/code_snapshot/"
cp "${UNIFY_EVAL_ROOT}/hle_0724_backend.py" "${RESULT_ROOT}/code_snapshot/"
cp "${HLE_VENDOR_ROOT}/run_evaluation_kimi_agent.py" "${RESULT_ROOT}/code_snapshot/"
cp "${HLE_VENDOR_ROOT}/hle_review.py" "${RESULT_ROOT}/code_snapshot/"
cp "${HLE_VENDOR_ROOT}/tools.py" "${RESULT_ROOT}/code_snapshot/"

case "${PHASE}" in
  outer1)
    printf '[%s] Filling HLE outer1 to %s cases\n' "$(date -u +%FT%TZ)" "${HLE_NUM_SAMPLES}"
    "${outer1_cmd[@]}" 2>&1 | tee -a "${RESULT_ROOT}/logs/hle_outer1_all.log"
    ;;
  chain)
    outer1_count="$(find -L "${OUTER1_ROOT}/HLE" -mindepth 2 -maxdepth 2 -name temp.json -printf '.\n' 2>/dev/null | wc -l)"
    [[ "${outer1_count}" -eq "${HLE_NUM_SAMPLES}" ]] || \
      die "outer1 is incomplete: ${outer1_count}/${HLE_NUM_SAMPLES}"
    printf '[%s] Starting HLE outer2->%s chains\n' "$(date -u +%FT%TZ)" "${MAX_OUTER}"
    "${chain_cmd[@]}" 2>&1 | tee -a "${RESULT_ROOT}/logs/hle_outer_chain.log"
    ;;
  all)
    printf '[%s] Starting unified HLE outer1->%s pipelines; concurrency=%s\n' \
      "$(date -u +%FT%TZ)" "${MAX_OUTER}" "${CONCURRENCY_LIMIT}"
    "${pipeline_cmd[@]}" 2>&1 | tee -a "${RESULT_ROOT}/logs/hle_pipeline.log"
    ;;
esac
