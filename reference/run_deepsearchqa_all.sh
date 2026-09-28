#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export DATASET_KEY=deepsearchqa DATASET_NAME=DeepSearch-QA DATASET_SIZE=900 DATASET_SHUFFLE=1
export EXPECTED_REUSABLE=100
export CONCURRENCY_LIMIT="${DEEPSEARCHQA_CONCURRENCY_LIMIT:-${CONCURRENCY_LIMIT:-100}}"
exec bash "${SCRIPT_DIR}/run_gaia_xbench_common.sh" "$@"
