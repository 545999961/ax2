#!/usr/bin/env bash
# HLE text items: one dataset, shared research evaluation settings.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
run_research_dataset "HLE" "$@"
