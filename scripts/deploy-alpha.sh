#!/usr/bin/env bash
# =============================================================================
# WaddleBot Alpha Deployment Script
# Local MicroK8s Deployment via Kustomize
#
# Usage:
#   ./scripts/deploy-alpha.sh [OPTIONS]
#
# Options:
#   --build               Build Docker images and import into MicroK8s (default)
#   --skip-build          Skip Docker build, use existing images
#   --tag TAG             Image tag to use (default: alpha)
#   --service SERVICE     Build/deploy specific service only
#   --dry-run             Show what would be deployed without applying
#   --rollback            Rollback deployments to previous revision
#   --help                Show this help message
#
# Environment:
#   KUBE_CONTEXT          Kubernetes context (default: local-alpha)
#   NAMESPACE             Target namespace (default: waddlebot-alpha)
#   APP_HOST              Application hostname (default: waddlebot.localhost.local)
#
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

readonly APP_NAME="${APP_NAME:-waddlebot}"
readonly KUBE_CONTEXT="${KUBE_CONTEXT:-local-alpha}"
readonly NAMESPACE="${NAMESPACE:-waddlebot}"
readonly APP_HOST="${APP_HOST:-waddlebot.localhost.local}"
readonly OVERLAY_PATH="${OVERLAY_PATH:-k8s/kustomize/overlays/alpha}"

# Services with their build context paths (relative to PROJECT_ROOT)
declare -A SERVICE_PATHS=(
    # Admin/Hub
    ["hub-api"]="admin/hub_module"
    ["hub-webui"]="admin/hub_module"
    # Core
    ["core-router"]="processing/router_module"
    ["core-identity"]="core/identity_core"
    ["core-labels"]="core/labels_core"
    ["core-browser-source"]="core/browser_source_core"
    ["core-reputation"]="core/reputation"
    ["core-community"]="core/community"
    ["core-ai-researcher"]="core/ai_researcher"
    ["core-video-proxy"]="core/video_proxy"
    ["core-engagement"]="core/engagement"
    ["core-module-rtc"]="core/module_rtc"
    # Collectors/Triggers
    ["collector-twitch"]="trigger/receiver/twitch"
    ["collector-discord"]="trigger/receiver/discord"
    ["collector-slack"]="trigger/receiver/slack"
    ["collector-youtube-live"]="trigger/receiver/youtube_live"
    ["collector-kick"]="trigger/receiver/kick_module_flask"
    # Interactive
    ["interactive-ai"]="action/interactive/ai"
    ["interactive-alias"]="action/interactive/alias"
    ["interactive-shoutout"]="action/interactive/shoutout"
    ["interactive-inventory"]="action/interactive/inventory"
    ["interactive-calendar"]="action/interactive/calendar"
    ["interactive-memories"]="action/interactive/memories"
    ["interactive-youtube-music"]="action/interactive/youtube_music"
    ["interactive-spotify"]="action/interactive/spotify"
    ["interactive-loyalty"]="action/interactive/loyalty"
    # Action/Pushing
    ["action-discord"]="action/pushing/discord"
    ["action-slack"]="action/pushing/slack"
    ["action-twitch"]="action/pushing/twitch"
    ["action-youtube"]="action/pushing/youtube"
    # Migrations
    ["waddlebot-migrations"]="migrations"
)

# Services that use a non-default Dockerfile name.
# Key: service name, Value: Dockerfile filename within the service path.
# Services not listed here fall back to Dockerfile.notests (if present) then Dockerfile.
declare -A SERVICE_DOCKERFILES=(
    ["hub-webui"]="Dockerfile.webui"
)

# Image name prefix (used for docker build tags)
readonly IMAGE_PREFIX="${APP_NAME}"

# Defaults
declare TAG="alpha"
declare SERVICE_FILTER=""
declare SKIP_BUILD=false
declare DRY_RUN=false
declare DO_ROLLBACK=false

# =============================================================================
# Color output helpers
# =============================================================================

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $*"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# =============================================================================
# kubectl wrapper (always uses --context)
# =============================================================================

kctl() {
    kubectl --context "${KUBE_CONTEXT}" "$@"
}

# =============================================================================
# Prerequisite checks
# =============================================================================

check_prerequisites() {
    print_info "Checking prerequisites..."
    local missing=()

    for cmd in kubectl docker microk8s; do
        if ! command -v "${cmd}" &>/dev/null; then
            missing+=("${cmd}")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing[*]}"
        exit 1
    fi

    # Verify context exists
    if ! kubectl config get-contexts "${KUBE_CONTEXT}" &>/dev/null; then
        print_error "Kubernetes context '${KUBE_CONTEXT}' not found"
        echo "Available contexts:"
        kubectl config get-contexts --output=name
        exit 1
    fi

    # Verify cluster reachable
    if ! kctl cluster-info &>/dev/null; then
        print_error "Cannot reach cluster via context '${KUBE_CONTEXT}'"
        print_error "Is MicroK8s running? Try: microk8s status"
        exit 1
    fi

    # Verify overlay exists
    if [[ ! -d "${PROJECT_ROOT}/${OVERLAY_PATH}" ]]; then
        print_error "Kustomize overlay not found: ${OVERLAY_PATH}"
        exit 1
    fi

    print_success "All prerequisites satisfied"
}

# =============================================================================
# Docker build and MicroK8s import
# =============================================================================

build_and_import() {
    local service="$1"
    local tag="$2"
    local service_path="${PROJECT_ROOT}/${SERVICE_PATHS[${service}]}"

    if [[ ! -d "${service_path}" ]]; then
        print_warning "Service directory not found: ${SERVICE_PATHS[${service}]} — skipping"
        return 0
    fi

    # Determine Dockerfile to use:
    #   1. SERVICE_DOCKERFILES entry (explicit override — e.g. hub-webui uses Dockerfile.webui)
    #   2. Dockerfile.notests (faster alpha build, skip test layers)
    #   3. Dockerfile (standard fallback)
    local dockerfile
    if [[ -n "${SERVICE_DOCKERFILES[${service}]+_}" ]]; then
        dockerfile="${service_path}/${SERVICE_DOCKERFILES[${service}]}"
        print_info "Using ${SERVICE_DOCKERFILES[${service}]} for ${service}"
    elif [[ -f "${service_path}/Dockerfile.notests" ]]; then
        dockerfile="${service_path}/Dockerfile.notests"
        print_info "Using Dockerfile.notests for ${service} (faster alpha build)"
    else
        dockerfile="${service_path}/Dockerfile"
    fi

    if [[ ! -f "${dockerfile}" ]]; then
        print_warning "No Dockerfile found for ${service} — skipping"
        return 0
    fi

    local image_name="${IMAGE_PREFIX}/${service}:${tag}"

    # Pass build args if set in environment
    local build_args=()
    if [[ -n "${NPM_TOKEN:-}" ]]; then
        build_args+=(--build-arg "NPM_TOKEN=${NPM_TOKEN}")
    fi

    print_info "Building image: ${image_name}"
    if ! docker build \
        --file "${dockerfile}" \
        --tag "${image_name}" \
        --label "environment=alpha" \
        --label "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        "${build_args[@]}" \
        "${PROJECT_ROOT}"; then
        print_error "Failed to build ${service}"
        return 1
    fi

    print_info "Importing ${image_name} into MicroK8s..."
    # Use MicroK8s's bundled ctr binary directly against the containerd socket.
    # This avoids the `microk8s ctr` wrapper which forces sudo even when the
    # user is already in the microk8s group.
    #
    # IMPORTANT: Use file-based import (not pipe). Piping docker save directly
    # into ctr silently produces a corrupt 276KB text/html manifest instead of
    # the real OCI image because ctr reads from stdin before the pipe is fully
    # buffered. Saving to a temp file first ensures all layer data is written
    # before ctr reads it.
    local mk8s_ctr="/snap/microk8s/current/bin/ctr"
    local mk8s_sock="/var/snap/microk8s/common/run/containerd.sock"
    local tmp_tar
    tmp_tar="$(mktemp /tmp/microk8s-import-XXXXXX.tar)"
    if ! docker save "${image_name}" -o "${tmp_tar}"; then
        rm -f "${tmp_tar}"
        print_error "Failed to save ${image_name} to tar"
        return 1
    fi
    if ! "${mk8s_ctr}" --address "${mk8s_sock}" -n k8s.io images import "${tmp_tar}"; then
        rm -f "${tmp_tar}"
        print_error "Failed to import ${image_name} into MicroK8s"
        return 1
    fi
    rm -f "${tmp_tar}"

    print_success "Built and imported: ${image_name}"
}

# =============================================================================
# Kustomize deployment
# =============================================================================

do_deploy() {
    print_info "Deploying to local MicroK8s cluster..."
    print_info "  Context:   ${KUBE_CONTEXT}"
    print_info "  Namespace: ${NAMESPACE}"
    print_info "  Overlay:   ${OVERLAY_PATH}"
    print_info "  Host:      ${APP_HOST}"

    # Create namespace if missing
    if ! kctl get namespace "${NAMESPACE}" &>/dev/null; then
        print_info "Creating namespace: ${NAMESPACE}"
        kctl create namespace "${NAMESPACE}"
    fi

    # Render kustomize and fix env var service references.
    # Kustomize namePrefix adds "alpha-" to resource names but not to
    # env var values that reference those services (e.g. DB_HOST, REDIS_HOST).
    # We post-process the rendered YAML to inject the prefix.
    local name_prefix
    name_prefix=$(grep 'namePrefix:' "${PROJECT_ROOT}/${OVERLAY_PATH}/kustomization.yaml" \
        | awk '{print $2}' | tr -d '"' || echo "")

    local rendered
    rendered=$(kubectl kustomize "${PROJECT_ROOT}/${OVERLAY_PATH}")
    if [[ -z "${rendered}" ]]; then
        print_error "Failed to render kustomize overlay"
        return 1
    fi

    if [[ -n "${name_prefix}" ]]; then
        print_info "Fixing service references for namePrefix: ${name_prefix}"
        # Kustomize renders unquoted values like: value: infra-postgres
        rendered=$(echo "${rendered}" | sed \
            -e "s|value: infra-postgres$|value: ${name_prefix}infra-postgres|g" \
            -e "s|value: infra-redis$|value: ${name_prefix}infra-redis|g" \
            -e "s|value: infra-minio|value: ${name_prefix}infra-minio|g" \
            -e "s|value: infra-qdrant|value: ${name_prefix}infra-qdrant|g" \
            -e "s|value: ai-ollama|value: ${name_prefix}ai-ollama|g" \
            -e "s|value: core-router|value: ${name_prefix}core-router|g" \
            -e "s|value: hub-api|value: ${name_prefix}hub-api|g" \
            -e "s|value: interactive-translate|value: ${name_prefix}interactive-translate|g" \
            -e "s|http://infra-|http://${name_prefix}infra-|g" \
            -e "s|http://interactive-|http://${name_prefix}interactive-|g" \
            -e "s|http://core-|http://${name_prefix}core-|g" \
        )
    fi

    # Apply kustomize overlay
    if [[ "${DRY_RUN}" == "true" ]]; then
        print_info "DRY-RUN: Rendering kustomize output..."
        echo "${rendered}"
        return 0
    fi

    if ! echo "${rendered}" | kctl apply -f -; then
        print_error "Failed to apply kustomize overlay"
        return 1
    fi

    print_success "Kustomize manifests applied"
}

# =============================================================================
# Rollout verification
# =============================================================================

wait_for_rollout() {
    print_info "Waiting for deployments to roll out..."

    # Get all deployments in namespace
    local deployments
    deployments=$(kctl get deployments -n "${NAMESPACE}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${deployments}" ]]; then
        print_warning "No deployments found in namespace ${NAMESPACE}"
        return 0
    fi

    local failed=false
    for deploy in ${deployments}; do
        print_info "Waiting for deployment/${deploy}..."
        if ! kctl rollout status "deployment/${deploy}" -n "${NAMESPACE}" --timeout=300s; then
            print_error "Deployment ${deploy} failed to roll out"
            failed=true
        fi
    done

    # Also check statefulsets
    local statefulsets
    statefulsets=$(kctl get statefulsets -n "${NAMESPACE}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    for sts in ${statefulsets}; do
        print_info "Waiting for statefulset/${sts}..."
        if ! kctl rollout status "statefulset/${sts}" -n "${NAMESPACE}" --timeout=300s; then
            print_error "StatefulSet ${sts} failed to roll out"
            failed=true
        fi
    done

    if [[ "${failed}" == "true" ]]; then
        return 1
    fi

    print_success "All workloads rolled out successfully"
}

# =============================================================================
# Show status
# =============================================================================

show_status() {
    echo ""
    print_info "Pod Status:"
    kctl get pods -n "${NAMESPACE}" -o wide
    echo ""
    print_info "Services:"
    kctl get svc -n "${NAMESPACE}"
    echo ""
    print_info "Access URL: https://${APP_HOST}"
    echo ""
    print_info "Quick commands:"
    echo "  View pods:   kubectl --context ${KUBE_CONTEXT} get pods -n ${NAMESPACE}"
    echo "  View logs:   kubectl --context ${KUBE_CONTEXT} logs -n ${NAMESPACE} -l environment=alpha -f"
    echo "  Describe:    kubectl --context ${KUBE_CONTEXT} describe pods -n ${NAMESPACE}"
}

# =============================================================================
# Rollback
# =============================================================================

do_rollback() {
    print_warning "Rolling back deployments in ${NAMESPACE}..."

    local deployments
    deployments=$(kctl get deployments -n "${NAMESPACE}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

    if [[ -z "${deployments}" ]]; then
        print_error "No deployments found in namespace ${NAMESPACE}"
        return 1
    fi

    for deploy in ${deployments}; do
        print_info "Rolling back deployment/${deploy}..."
        kctl rollout undo "deployment/${deploy}" -n "${NAMESPACE}"
    done

    print_success "Rollback initiated"
    wait_for_rollout
}

# =============================================================================
# Help
# =============================================================================

show_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deploy ${APP_NAME} to local MicroK8s alpha environment using Kustomize.

OPTIONS:
    --build               Build images and import into MicroK8s (default)
    --skip-build          Skip Docker build, use existing images
    --tag TAG             Image tag (default: alpha)
    --service SERVICE     Build specific service only
    --dry-run             Render manifests without applying
    --rollback            Rollback deployments to previous revision
    --help                Show this help message

ENVIRONMENT:
    KUBE_CONTEXT:   ${KUBE_CONTEXT}
    NAMESPACE:      ${NAMESPACE}
    APP_HOST:       ${APP_HOST}
    OVERLAY_PATH:   ${OVERLAY_PATH}

SERVICES (Admin/Hub):
    hub-api                (admin/hub_module — Dockerfile)
    hub-webui              (admin/hub_module — Dockerfile.webui)

SERVICES (Core):
    core-router            (processing/router_module)
    core-identity          (core/identity_core)
    core-labels            (core/labels_core)
    core-browser-source    (core/browser_source_core)
    core-reputation        (core/reputation)
    core-community         (core/community)
    core-ai-researcher     (core/ai_researcher)
    core-video-proxy       (core/video_proxy)
    core-engagement        (core/engagement)
    core-module-rtc        (core/module_rtc)

SERVICES (Collectors/Triggers):
    collector-twitch       (trigger/receiver/twitch)
    collector-discord      (trigger/receiver/discord)
    collector-slack        (trigger/receiver/slack)
    collector-youtube-live (trigger/receiver/youtube_live)
    collector-kick         (trigger/receiver/kick_module_flask)

SERVICES (Interactive):
    interactive-ai         (action/interactive/ai)
    interactive-alias      (action/interactive/alias)
    interactive-shoutout   (action/interactive/shoutout)
    interactive-inventory  (action/interactive/inventory)
    interactive-calendar   (action/interactive/calendar)
    interactive-memories   (action/interactive/memories)
    interactive-youtube-music (action/interactive/youtube_music)
    interactive-spotify    (action/interactive/spotify)
    interactive-loyalty    (action/interactive/loyalty)

SERVICES (Action/Pushing):
    action-discord         (action/pushing/discord)
    action-slack           (action/pushing/slack)
    action-twitch          (action/pushing/twitch)
    action-youtube         (action/pushing/youtube)

SERVICES (Migrations):
    waddlebot-migrations   (migrations)

EXAMPLES:
    # Full build and deploy
    $(basename "$0")

    # Deploy without rebuilding images
    $(basename "$0") --skip-build

    # Build and deploy only one service
    $(basename "$0") --service hub-api

    # Preview what would be applied
    $(basename "$0") --skip-build --dry-run

    # Rollback to previous deployment
    $(basename "$0") --rollback
EOF
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --build)
                SKIP_BUILD=false
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --tag)
                TAG="$2"
                shift 2
                ;;
            --service)
                SERVICE_FILTER="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --rollback)
                DO_ROLLBACK=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    echo ""
    print_info "=========================================="
    print_info "  ${APP_NAME} — Alpha Deployment"
    print_info "=========================================="
    echo ""

    check_prerequisites

    # Handle rollback
    if [[ "${DO_ROLLBACK}" == "true" ]]; then
        do_rollback
        show_status
        exit $?
    fi

    # Build images
    if [[ "${SKIP_BUILD}" != "true" ]]; then
        print_info "Building and importing Docker images..."
        for service in "${!SERVICE_PATHS[@]}"; do
            if [[ -z "${SERVICE_FILTER}" ]] || [[ "${SERVICE_FILTER}" == "${service}" ]]; then
                build_and_import "${service}" "${TAG}" || {
                    print_error "Failed to build ${service}"
                    exit 1
                }
            fi
        done
    else
        print_info "Skipping build (--skip-build)"
    fi

    # Deploy
    do_deploy || exit 1

    if [[ "${DRY_RUN}" != "true" ]]; then
        wait_for_rollout || print_warning "Some workloads did not roll out cleanly"
        show_status
        print_success "Alpha deployment complete!"
    else
        print_success "Dry-run complete!"
    fi
}

main "$@"
