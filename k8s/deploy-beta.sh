#!/bin/bash
# WaddleBot Beta Cluster Deployment Script
# Builds images, pushes to registry, and deploys to beta K8s cluster

set -e  # Exit on any error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="registry-dal2.penguintech.io/waddlebot"
NAMESPACE="waddlebot"
HELM_CHART="./k8s/helm/waddlebot"
TAG="${1:-latest}"  # Use first argument as tag, default to 'latest'

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Pre-flight checks
print_info "Running pre-flight checks..."

if ! command_exists docker; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! command_exists kubectl; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

if ! command_exists helm; then
    print_error "Helm is not installed or not in PATH"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] || [ ! -d "admin/hub_module" ]; then
    print_error "This script must be run from the WaddleBot root directory"
    exit 1
fi

print_success "Pre-flight checks passed"

# Check for NPM_TOKEN (required for @penguintechinc packages from GitHub Packages)
if [ -z "${NPM_TOKEN}" ]; then
    if [ -f "$HOME/code/.gh-token" ]; then
        export NPM_TOKEN=$(grep -v '^#' "$HOME/code/.gh-token" | grep -v '^$' | head -1)
        print_info "Loaded NPM_TOKEN from ~/code/.gh-token"
    else
        print_error "NPM_TOKEN is not set and ~/code/.gh-token not found"
        print_error "Set NPM_TOKEN env var with a GitHub token that has read:packages scope"
        exit 1
    fi
fi

# Step 1: Build hub-webui image
print_info "Building hub-webui image..."
docker build \
    -f admin/hub_module/Dockerfile.webui \
    --build-arg NPM_TOKEN=${NPM_TOKEN} \
    -t ${REGISTRY}/hub-webui:${TAG} \
    .

if [ $? -eq 0 ]; then
    print_success "hub-webui image built successfully"
else
    print_error "Failed to build hub-webui image"
    exit 1
fi

# Step 2: Build hub-api image
print_info "Building hub-api image..."
docker build \
    -f admin/hub_module/Dockerfile \
    --build-arg NPM_TOKEN=${NPM_TOKEN} \
    -t ${REGISTRY}/hub-api:${TAG} \
    .

if [ $? -eq 0 ]; then
    print_success "hub-api image built successfully"
else
    print_error "Failed to build hub-api image"
    exit 1
fi

# Step 3: Push hub-webui image
print_info "Pushing hub-webui image to registry..."
docker push ${REGISTRY}/hub-webui:${TAG}

if [ $? -eq 0 ]; then
    print_success "hub-webui image pushed successfully"
else
    print_error "Failed to push hub-webui image"
    exit 1
fi

# Step 4: Push hub-api image
print_info "Pushing hub-api image to registry..."
docker push ${REGISTRY}/hub-api:${TAG}

if [ $? -eq 0 ]; then
    print_success "hub-api image pushed successfully"
else
    print_error "Failed to push hub-api image"
    exit 1
fi

# Step 5: Check if namespace exists
print_info "Checking if namespace ${NAMESPACE} exists..."
if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
    print_warning "Namespace ${NAMESPACE} does not exist, creating..."
    kubectl create namespace ${NAMESPACE}
    print_success "Namespace ${NAMESPACE} created"
else
    print_success "Namespace ${NAMESPACE} already exists"
fi

# Step 6: Deploy/Upgrade Helm chart
print_info "Deploying to beta cluster with Helm..."
helm upgrade waddlebot ${HELM_CHART} \
    --install \
    --namespace ${NAMESPACE} \
    -f ${HELM_CHART}/values.yaml \
    -f ${HELM_CHART}/values-beta.yaml \
    --set global.imageTag=${TAG} \
    --timeout 10m \
    --wait

if [ $? -eq 0 ]; then
    print_success "Helm deployment successful"
else
    print_error "Helm deployment failed"
    exit 1
fi

# Step 7: Force restart hub services to pull new images
print_info "Restarting hub-api deployment..."
kubectl rollout restart deployment waddlebot-hub-api -n ${NAMESPACE} || print_warning "hub-api deployment not found, skipping restart"

print_info "Restarting hub-webui deployment..."
kubectl rollout restart deployment waddlebot-hub-webui -n ${NAMESPACE} || print_warning "hub-webui deployment not found, skipping restart"

# Step 8: Wait for rollout to complete
print_info "Waiting for hub-api rollout to complete..."
kubectl rollout status deployment waddlebot-hub-api -n ${NAMESPACE} --timeout=5m || print_warning "hub-api rollout status unavailable"

print_info "Waiting for hub-webui rollout to complete..."
kubectl rollout status deployment waddlebot-hub-webui -n ${NAMESPACE} --timeout=5m || print_warning "hub-webui rollout status unavailable"

# Step 9: Display deployment status
print_info "Deployment Status:"
echo ""
kubectl get pods -n ${NAMESPACE} | grep -E "hub-api|hub-webui" || echo "No hub pods found"
echo ""

# Step 10: Display ingress information
print_info "Ingress Information:"
echo ""
kubectl get ingress -n ${NAMESPACE} || echo "No ingress found"
echo ""

print_success "==================================="
print_success "Beta deployment completed!"
print_success "==================================="
print_info "WebUI: https://waddlebot.penguintech.io/"
print_info "API: https://waddlebot.penguintech.io/api"
echo ""
print_info "To view logs:"
print_info "  kubectl logs -f deployment/waddlebot-hub-api -n ${NAMESPACE}"
print_info "  kubectl logs -f deployment/waddlebot-hub-webui -n ${NAMESPACE}"
echo ""
print_info "To check pod status:"
print_info "  kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/component=hub"
print_info "  kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/component=hub-webui"
