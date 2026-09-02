#!/usr/bin/env bash
# Installs every Python dependency `make test-unit` / tests/k8s/alpha/05-unit-tests.sh
# needs to collect and run the full unit suite (legacy tests/unit +
# identity_core_module, hub_api, libs/* (flask_core + SCCEMBS module
# libraries), and every core/svc_* stage-runner container).
#
# Each subproject ships its own requirements.txt with its own pins -- most
# are hash-pinned (--require-hashes) and some legitimately disagree on
# transitive pins (e.g. hub_api pins pydal==20260520.0 while svc_action pins
# pydal==20241204.1). pip's --require-hashes rejects mixing hashed and
# unhashed/editable specs in the same invocation, so each requirements.txt
# is installed as its own separate `pip install` call, in order -- a later
# step's pin wins for shared deps, which matches what each subproject's own
# test suite is actually verified against. This is the single source of
# truth for the install sequence; .github/workflows/pr-validation.yml calls
# this same script so CI and local runs never drift.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
    echo "Required Python executable not found: $PYTHON_BIN" >&2
    exit 127
}

PIP=("$PYTHON_BIN" -m pip install --disable-pip-version-check)

echo "[install-unit-test-deps] core/identity_core_module + editable libs/flask_core"
"${PIP[@]}" -r core/identity_core_module/requirements.txt -e libs/flask_core

for pkg in hub_api core/svc_action core/svc_ingest core/svc_presentation core/svc_process core/svc_streaming; do
    req="${pkg}/requirements.txt"
    if [ ! -f "$req" ]; then
        echo "[install-unit-test-deps] ERROR: $req not found" >&2
        exit 1
    fi
    echo "[install-unit-test-deps] ${pkg}"
    "${PIP[@]}" --require-hashes -r "$req"
done

echo "[install-unit-test-deps] done"
