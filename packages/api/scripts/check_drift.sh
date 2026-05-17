#!/usr/bin/env bash
# check_drift.sh — CI drift detection for generated code.
# Exit 0 if generated files match, exit 1 if they are stale.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$(dirname "$SCRIPT_DIR")"

cd "$API_DIR"

python -m scripts.codegen --check
