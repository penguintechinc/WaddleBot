#!/bin/bash
# setup-ghcr-pull-secret.sh
# Creates (or replaces) the ghcr-pull-secret in the waddlebot namespace on dal2-beta.
# Run once before first ghcr.io-based deployment and whenever the token rotates.
#
# Requires: kubectl with dal2-beta context configured
# Token source: ~/code/.gh-token line 4 (full-access token with read:packages scope)

set -euo pipefail

KUBE_CONTEXT="dal2-beta"
NAMESPACE="waddlebot"
SECRET_NAME="ghcr-pull-secret"
GHCR_SERVER="ghcr.io"
GHCR_USER="penguintechinc"

# Ensure namespace exists
kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" > /dev/null 2>&1 || \
    kubectl --context "$KUBE_CONTEXT" create namespace "$NAMESPACE"

# Read token without exposing it in shell history or process list
if [ ! -f "$HOME/code/.gh-token" ]; then
    echo "ERROR: ~/code/.gh-token not found"
    exit 1
fi

read -r GHCR_TOKEN < <(sed -n '4p' "$HOME/code/.gh-token")

if [ -z "$GHCR_TOKEN" ]; then
    echo "ERROR: Could not read token from ~/code/.gh-token line 4"
    exit 1
fi

# Create/update the pull secret idempotently via dry-run + apply
kubectl create secret docker-registry "$SECRET_NAME" \
    --context "$KUBE_CONTEXT" \
    --namespace "$NAMESPACE" \
    --docker-server="$GHCR_SERVER" \
    --docker-username="$GHCR_USER" \
    --docker-password="$GHCR_TOKEN" \
    --dry-run=client -o yaml \
    | kubectl apply --context "$KUBE_CONTEXT" -f -

unset GHCR_TOKEN

echo "✅ ${SECRET_NAME} updated in namespace ${NAMESPACE} on context ${KUBE_CONTEXT}"
