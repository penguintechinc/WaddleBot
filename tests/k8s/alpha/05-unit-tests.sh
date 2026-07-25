#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export PROJECT_NAME="$(basename "$REPO_ROOT")"
export NAMESPACE="${PROJECT_NAME}-alpha"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_info "Running unit tests"
cd "$REPO_ROOT"

# Tests import repository packages directly. The environment running this script
# must install the module dependencies (including pytest/pytest-asyncio and the
# identity module requirements); flask_core is loaded from its local source tree.
export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/core:$REPO_ROOT/libs/flask_core${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
    echo "Required Python executable not found: $PYTHON_BIN" >&2
    exit 127
}

"$PYTHON_BIN" -m pytest \
    tests/unit \
    core/identity_core_module/services/test_grpc_handler.py

log_pass "Unit tests step completed"
