#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export DATASET_KEY=xbench DATASET_NAME=xBench-DeepSearch-2510 DATASET_SIZE=100
export CONCURRENCY_LIMIT="${XBENCH_CONCURRENCY_LIMIT:-${CONCURRENCY_LIMIT:-50}}"
exec bash "${SCRIPT_DIR}/run_gaia_xbench_common.sh" "$@"
