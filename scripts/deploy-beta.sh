#!/bin/bash
# WaddleBot Beta Cluster Deployment Script
# Standardized deployment with CLI argument parsing
# Builds images, pushes to registry, and deploys to beta K8s cluster

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="registry-dal2.penguintech.io/waddlebot"
NAMESPACE="waddlebot"
HELM_CHART="${PROJECT_ROOT}/k8s/helm/waddlebot"
KUBE_CONTEXT="dal2-beta"

# Services to build and push
declare -A SERVICES=(
    [hub-api]="${PROJECT_ROOT}/admin/hub_module/Dockerfile"
    [hub-webui]="${PROJECT_ROOT}/admin/hub_module/Dockerfile.webui"
    [core-video-proxy]="${PROJECT_ROOT}/services/video-proxy/Dockerfile"
    [core-engagement]="${PROJECT_ROOT}/services/engagement/Dockerfile"
    [core-module-rtc]="${PROJECT_ROOT}/services/module-rtc/Dockerfile"
)

# Default values — unique epoch tag per skill (never reuse beta-latest)
TAG="${TAG:-beta-$(date +%s)}"
SERVICES_TO_BUILD=()
SKIP_BUILD=false
DRY_RUN=false
DO_ROLLBACK=false
SHOW_HELP=false

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_section() {
    echo ""
    echo -e "${CYAN}===================================================${NC}"
    echo -e "${CYAN}$*${NC}"
    echo -e "${CYAN}===================================================${NC}"
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print usage
print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OPTIONS:
  --tag TAG              Image tag to build and deploy (default: latest)
  --service SERVICE      Build and deploy specific service (can be used multiple times)
  --skip-build           Skip building images, only deploy (requires pre-built images)
  --dry-run              Show what would be done without making changes
  --rollback             Rollback to previous deployment
  --help                 Show this help message

SERVICES:
  hub-api
  hub-webui
  core-video-proxy
  core-engagement
  core-module-rtc

EXAMPLES:
  # Deploy all services with a specific tag
  $0 --tag v1.2.3

  # Deploy only hub-api
  $0 --service hub-api

  # Deploy multiple services
  $0 --service hub-api --service core-engagement

  # Skip build and deploy pre-built images
  $0 --skip-build --tag my-custom-tag

  # Rollback to previous version
  $0 --rollback

  # Dry run to see what would be deployed
  $0 --dry-run

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            TAG="$2"
            shift 2
            ;;
        --service)
            SERVICES_TO_BUILD+=("$2")
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
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
            print_usage
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            ;;
    esac
done

# If no specific services selected, build all
if [ ${#SERVICES_TO_BUILD[@]} -eq 0 ] && [ "$SKIP_BUILD" = false ]; then
    SERVICES_TO_BUILD=("${!SERVICES[@]}")
fi

# Check prerequisites
check_prerequisites() {
    log_section "Checking Prerequisites"

    if ! command_exists docker; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    log_success "Docker found: $(docker --version)"

    if ! command_exists kubectl; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    log_success "kubectl found: $(kubectl version --client --short 2>/dev/null || echo 'installed')"

    if ! command_exists helm; then
        log_error "Helm is not installed or not in PATH"
        exit 1
    fi
    log_success "Helm found: $(helm version --short 2>/dev/null || echo 'installed')"

    # Check if we're in the right directory
    if [ ! -f "${PROJECT_ROOT}/docker-compose.yml" ] || [ ! -d "${PROJECT_ROOT}/admin/hub_module" ]; then
        log_error "This script must be run from the WaddleBot root directory"
        exit 1
    fi
    log_success "WaddleBot project directory verified"

    # Verify kubectl context
    current_context=$(kubectl config current-context 2>/dev/null || echo "")
    if [ -z "$current_context" ]; then
        log_warning "No Kubernetes context set, using default"
    else
        log_success "Kubernetes context: $current_context"
    fi

    # Check for NPM_TOKEN
    if [ -z "${NPM_TOKEN:-}" ]; then
        if [ -f "$HOME/code/.gh-token" ]; then
            export NPM_TOKEN=$(grep -v '^#' "$HOME/code/.gh-token" | grep -v '^$' | head -1)
            log_info "Loaded NPM_TOKEN from ~/code/.gh-token"
        else
            log_error "NPM_TOKEN is not set and ~/code/.gh-token not found"
            log_error "Set NPM_TOKEN env var with a GitHub token that has read:packages scope"
            exit 1
        fi
    fi
    log_success "NPM_TOKEN configured"
}

# Build and push images
build_and_push_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log_section "Skipping Image Build (--skip-build flag set)"
        return 0
    fi

    log_section "Building and Pushing Docker Images"

    for service in "${SERVICES_TO_BUILD[@]}"; do
        if [ ! -v "SERVICES[$service]" ]; then
            log_error "Unknown service: $service"
            exit 1
        fi

        dockerfile="${SERVICES[$service]}"
        image_name="${service}"

        log_info "Building ${image_name}..."

        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY-RUN] docker build -f ${dockerfile} --build-arg NPM_TOKEN=*** -t waddlebot-${image_name}:latest ${PROJECT_ROOT}"
            log_info "[DRY-RUN] docker tag waddlebot-${image_name}:latest ${REGISTRY}/${image_name}:${TAG}"
            log_info "[DRY-RUN] docker push ${REGISTRY}/${image_name}:${TAG}"
        else
            # Build locally first (never use buildx --push against beta registry)
            if ! docker build \
                -f "${dockerfile}" \
                --build-arg NPM_TOKEN="${NPM_TOKEN}" \
                -t "waddlebot-${image_name}:latest" \
                "${PROJECT_ROOT}"; then
                log_error "Failed to build ${image_name} image"
                exit 1
            fi
            log_success "${image_name} image built successfully"

            # Tag for beta registry (separate step per skill)
            log_info "Tagging ${image_name} for beta registry..."
            docker tag "waddlebot-${image_name}:latest" "${REGISTRY}/${image_name}:${TAG}"
            log_success "${image_name} tagged as ${REGISTRY}/${image_name}:${TAG}"

            # Push to beta registry (separate step — never use buildx --push)
            log_info "Pushing ${image_name} image to registry..."
            if ! docker push "${REGISTRY}/${image_name}:${TAG}"; then
                log_error "Failed to push ${image_name} image"
                exit 1
            fi
            log_success "${image_name} image pushed successfully"
        fi
    done
}

# Deploy via Helm
do_deploy() {
    log_section "Deploying to Beta Cluster with Helm"

    # Create namespace if it doesn't exist
    log_info "Checking if namespace ${NAMESPACE} exists..."
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] kubectl --context ${KUBE_CONTEXT} get namespace ${NAMESPACE}"
    else
        if ! kubectl --context "${KUBE_CONTEXT}" get namespace "${NAMESPACE}" &>/dev/null; then
            log_warning "Namespace ${NAMESPACE} does not exist, creating..."
            kubectl --context "${KUBE_CONTEXT}" create namespace "${NAMESPACE}" || true
            log_success "Namespace ${NAMESPACE} created"
        else
            log_success "Namespace ${NAMESPACE} already exists"
        fi
    fi

    # Deploy/Upgrade Helm chart
    log_info "Deploying WaddleBot to beta cluster..."

    helm_cmd="helm upgrade waddlebot ${HELM_CHART} \
        --install \
        --kube-context ${KUBE_CONTEXT} \
        --namespace ${NAMESPACE} \
        -f ${HELM_CHART}/values.yaml \
        -f ${HELM_CHART}/values-beta.yaml \
        --set global.imageTag=${TAG} \
        --timeout 10m \
        --wait"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] ${helm_cmd}"
    else
        if ! eval "${helm_cmd}"; then
            log_error "Helm deployment failed"
            exit 1
        fi
        log_success "Helm deployment successful"
    fi
}

# Restart deployments to pick up new images
verify_deployment() {
    log_section "Verifying Deployment"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would restart deployments and verify rollout"
        return 0
    fi

    # Force restart hub services to pull new images
    log_info "Restarting hub-api deployment..."
    kubectl --context "${KUBE_CONTEXT}" rollout restart deployment waddlebot-hub-api -n "${NAMESPACE}" 2>/dev/null || log_warning "hub-api deployment not found, skipping restart"

    log_info "Restarting hub-webui deployment..."
    kubectl --context "${KUBE_CONTEXT}" rollout restart deployment waddlebot-hub-webui -n "${NAMESPACE}" 2>/dev/null || log_warning "hub-webui deployment not found, skipping restart"

    # Wait for rollout to complete
    log_info "Waiting for hub-api rollout to complete..."
    kubectl --context "${KUBE_CONTEXT}" rollout status deployment waddlebot-hub-api -n "${NAMESPACE}" --timeout=5m 2>/dev/null || log_warning "hub-api rollout status unavailable"

    log_info "Waiting for hub-webui rollout to complete..."
    kubectl --context "${KUBE_CONTEXT}" rollout status deployment waddlebot-hub-webui -n "${NAMESPACE}" --timeout=5m 2>/dev/null || log_warning "hub-webui rollout status unavailable"

    # Verify pods picked up the new image
    log_info "Verifying pods are running the expected image tag (${TAG})..."
    echo ""
    VERIFY_FAILED=false
    for svc in hub-api hub-webui; do
        POD_IMAGE=$(kubectl --context "${KUBE_CONTEXT}" get pods -n "${NAMESPACE}" \
            -l "app.kubernetes.io/name=waddlebot-${svc}" \
            -o jsonpath='{.items[0].spec.containers[0].image}' 2>/dev/null || echo "")
        if [ -z "${POD_IMAGE}" ]; then
            log_warning "${svc}: no pods found"
            VERIFY_FAILED=true
        elif echo "${POD_IMAGE}" | grep -q "${TAG}"; then
            log_success "${svc} running: ${POD_IMAGE}"
        else
            log_warning "${svc} image mismatch! Expected tag ${TAG}, got: ${POD_IMAGE}"
            VERIFY_FAILED=true
        fi
    done
    if [ "$VERIFY_FAILED" = true ]; then
        log_warning "Some pods may not have picked up the new image. Check manually:"
        log_warning "  kubectl --context ${KUBE_CONTEXT} get pods -n ${NAMESPACE} -o wide"
    fi
    echo ""

    # Display deployment status
    log_info "Deployment Status:"
    echo ""
    kubectl --context "${KUBE_CONTEXT}" get pods -n "${NAMESPACE}" | grep -E "hub-api|hub-webui" || echo "No hub pods found"
    echo ""

    # Display ingress information
    log_info "Ingress Information:"
    echo ""
    kubectl --context "${KUBE_CONTEXT}" get ingress -n "${NAMESPACE}" || echo "No ingress found"
    echo ""
}

# Rollback to previous deployment
do_rollback() {
    log_section "Rolling Back Deployment"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would rollback to previous release"
        return 0
    fi

    log_info "Rolling back Helm release..."
    if helm --kube-context "${KUBE_CONTEXT}" rollback waddlebot -n "${NAMESPACE}"; then
        log_success "Rollback successful"
    else
        log_error "Rollback failed"
        exit 1
    fi

    verify_deployment
}

# Main execution
main() {
    log_section "WaddleBot Beta Deployment Script"
    log_info "Tag: ${TAG}"
    log_info "Namespace: ${NAMESPACE}"
    log_info "Kube Context: ${KUBE_CONTEXT}"
    if [ "$DRY_RUN" = true ]; then
        log_warning "Running in DRY-RUN mode - no changes will be made"
    fi

    check_prerequisites

    if [ "$DO_ROLLBACK" = true ]; then
        do_rollback
    else
        build_and_push_images
        do_deploy
        verify_deployment
    fi

    log_section "Deployment Complete"
    log_success "==================================="
    log_success "Beta deployment completed!"
    log_success "==================================="
    log_info "WebUI: https://waddlebot.penguintech.io/"
    log_info "API: https://waddlebot.penguintech.io/api"
    echo ""
    log_info "To view logs:"
    log_info "  kubectl --context ${KUBE_CONTEXT} logs -f deployment/waddlebot-hub-api -n ${NAMESPACE}"
    log_info "  kubectl --context ${KUBE_CONTEXT} logs -f deployment/waddlebot-hub-webui -n ${NAMESPACE}"
    echo ""
    log_info "To check pod status:"
    log_info "  kubectl --context ${KUBE_CONTEXT} get pods -n ${NAMESPACE} -l app.kubernetes.io/component=hub"
    log_info "  kubectl --context ${KUBE_CONTEXT} get pods -n ${NAMESPACE} -l app.kubernetes.io/component=hub-webui"
    echo ""
}

# Run main function
main
