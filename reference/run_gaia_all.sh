#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export DATASET_KEY=gaia DATASET_NAME=GAIA-2023-validation-text-103 DATASET_SIZE=103
export CONCURRENCY_LIMIT="${GAIA_CONCURRENCY_LIMIT:-${CONCURRENCY_LIMIT:-50}}"
exec bash "${SCRIPT_DIR}/run_gaia_xbench_common.sh" "$@"
