# Waddles Kubernetes Installation Guide

This directory contains automated installation scripts for deploying Waddles to Kubernetes clusters.

## Installation Scripts

- **`install-microk8s.sh`** - For MicroK8s clusters (Ubuntu/Debian)
- **`install-k8s.sh`** - For CNCF Kubernetes (kind, minikube, kubeadm, etc.)

## Quick Start

### MicroK8s Installation

```bash
# Install Waddles with Helm (recommended)
./install-microk8s.sh --build-images

# Or use raw manifests
./install-microk8s.sh --manifests --build-images

# Uninstall
./install-microk8s.sh --uninstall
```

### CNCF Kubernetes Installation

#### Using kind (local development)

```bash
# Create kind cluster and deploy Waddles
./install-k8s.sh --kind --build-images

# Uninstall
./install-k8s.sh --kind --uninstall
```

#### Using minikube

```bash
# Start minikube and deploy Waddles
./install-k8s.sh --minikube --build-images

# Uninstall
./install-k8s.sh --minikube --uninstall
```

#### Using existing cluster

```bash
# Deploy to existing cluster
./install-k8s.sh --registry your-registry.io --build-images

# With custom storage and ingress classes
./install-k8s.sh \
  --registry gcr.io/my-project \
  --storage-class gp2 \
  --ingress-class alb \
  --build-images
```

## Prerequisites

### MicroK8s

- Ubuntu/Debian Linux
- snap package manager
- 8GB RAM minimum
- 50GB disk space

The script will automatically install:
- MicroK8s (if not installed)
- Helm 3.x (if using `--helm`)

### CNCF Kubernetes

- kubectl 1.23+
- Helm 3.x (for Helm deployments)
- Docker (for building images)
- kind or minikube (if using local clusters)

## Script Options

### install-microk8s.sh

```
Options:
  --helm              Use Helm chart for deployment (default)
  --manifests         Use raw Kubernetes manifests for deployment
  --build-images      Build and push Docker images to cluster registry
  --skip-build        Skip image building (use existing images)
  --skip-setup        Skip MicroK8s setup and addon enabling
  --namespace NAME    Use custom namespace (default: waddlebot)
  --uninstall         Uninstall WaddleBot from the cluster
  --help              Show help message
```

### install-k8s.sh

```
Options:
  --helm              Use Helm chart for deployment (default)
  --manifests         Use raw Kubernetes manifests for deployment
  --build-images      Build and push Docker images to registry
  --skip-build        Skip image building (use existing images)
  --registry URL      Container registry URL (default: localhost:5000)
  --context NAME      Kubernetes context to use (default: current)
  --namespace NAME    Use custom namespace (default: waddlebot)
  --storage-class     StorageClass to use (default: standard)
  --ingress-class     IngressClass to use (default: nginx)
  --kind              Setup and deploy to kind cluster
  --minikube          Setup and deploy to minikube cluster
  --uninstall         Uninstall WaddleBot from the cluster
  --help              Show help message
```

## Deployment Methods

### Helm Chart (Recommended)

Helm provides templating, easy upgrades, and configuration management.

**Advantages:**
- Easy configuration via values files
- Simple upgrades: `helm upgrade`
- Rollback support: `helm rollback`
- Release management

**Usage:**
```bash
# MicroK8s
./install-microk8s.sh --helm --build-images

# CNCF Kubernetes
./install-k8s.sh --helm --build-images
```

### Raw Manifests

Direct Kubernetes manifests with Kustomize for configuration.

**Advantages:**
- Simple, transparent YAML files
- No Helm dependency
- Direct kubectl control

**Usage:**
```bash
# MicroK8s
./install-microk8s.sh --manifests --build-images

# CNCF Kubernetes
./install-k8s.sh --manifests --build-images
```

## Image Building

### With Image Building (First Install)

```bash
# Build all Docker images and push to cluster registry
./install-microk8s.sh --build-images
```

This will:
1. Build all WaddleBot module Docker images
2. Tag them for the cluster registry
3. Push to the cluster registry (localhost:32000 for MicroK8s, localhost:5000 for kind/minikube)
4. Deploy WaddleBot

### Without Image Building (Updates/Reinstalls)

```bash
# Use existing images in registry
./install-microk8s.sh --skip-build
```

## Registry Configuration

### MicroK8s

Uses built-in registry: `localhost:32000/waddlebot`

Enable with:
```bash
microk8s enable registry
```

### kind

Creates local registry: `localhost:5000/waddlebot`

Automatically created by the script when using `--kind`

### minikube

Uses minikube registry addon: `localhost:5000/waddlebot`

Enable with:
```bash
minikube addons enable registry
```

### Custom Registry

```bash
# Use your own registry
./install-k8s.sh --registry gcr.io/my-project/waddlebot --build-images
```

## Accessing WaddleBot

After installation, WaddleBot is accessible at:

### Via Ingress

Add to `/etc/hosts`:
```
127.0.0.1 waddlebot.local
```

Then access:
- http://waddlebot.local

### Via NodePort (MicroK8s)

- http://localhost:30080

### Via Port Forward

```bash
kubectl port-forward -n waddlebot svc/hub 8060:8060
```

Then access:
- http://localhost:8060

## Verification

Check deployment status:

```bash
# List all pods
kubectl get pods -n waddlebot

# Check services
kubectl get svc -n waddlebot

# View ingress
kubectl get ingress -n waddlebot

# View logs
kubectl logs -n waddlebot deployment/hub --tail=50
kubectl logs -n waddlebot deployment/router --tail=50
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod details
kubectl describe pod -n waddlebot <pod-name>

# View logs
kubectl logs -n waddlebot <pod-name>

# Check events
kubectl get events -n waddlebot --sort-by='.lastTimestamp'
```

### Image Pull Errors

**MicroK8s:**
```bash
# Verify registry is enabled
microk8s enable registry

# Check registry is accessible
curl http://localhost:32000/v2/_catalog

# Rebuild and push images
./install-microk8s.sh --build-images
```

**kind:**
```bash
# Verify registry is running
docker ps | grep kind-registry

# Check registry contents
curl http://localhost:5000/v2/_catalog
```

### Database Connection Issues

```bash
# Check postgres is running
kubectl get pod -n waddlebot -l app.kubernetes.io/name=postgres

# Test connection from router pod
kubectl exec -n waddlebot deployment/router -- \
  python3 -c "import psycopg2; psycopg2.connect('postgresql://waddlebot:waddlebot_secret@postgres:5432/waddlebot')"
```

### Storage Issues

```bash
# Check PVCs
kubectl get pvc -n waddlebot

# Describe PVC for details
kubectl describe pvc -n waddlebot postgres-pvc

# MicroK8s: Enable storage
microk8s enable storage

# kind/minikube: Storage is enabled by default
```

### Ingress Not Working

```bash
# Check ingress status
kubectl describe ingress -n waddlebot waddlebot-ingress

# Check ingress controller pods
kubectl get pods -n ingress-nginx

# MicroK8s: Enable ingress
microk8s enable ingress

# kind: Ingress installed automatically by script
# minikube: Enable ingress addon
minikube addons enable ingress
```

## Customization

### Custom Namespace

```bash
./install-microk8s.sh --namespace my-waddlebot --build-images
```

### Custom Storage Class

```bash
./install-k8s.sh --storage-class gp2 --build-images
```

### Custom Ingress Class

```bash
./install-k8s.sh --ingress-class alb --build-images
```

### Multiple Clusters

```bash
# Deploy to specific context
./install-k8s.sh --context production --build-images

# Deploy to different namespaces
./install-k8s.sh --namespace waddlebot-dev --build-images
./install-k8s.sh --namespace waddlebot-staging --build-images
```

## Upgrading

### Helm Upgrade

```bash
# Update configuration in values files
vim k8s/helm/waddlebot/values-local.yaml

# Upgrade deployment
helm upgrade waddlebot ./k8s/helm/waddlebot \
  -f ./k8s/helm/waddlebot/values-local.yaml \
  -n waddlebot
```

### Manifest Upgrade

```bash
# Update manifests
vim k8s/manifests/core/hub.yaml

# Apply changes
kubectl apply -k ./k8s/manifests/
```

### Rebuild and Upgrade

```bash
# Rebuild images and upgrade
./install-microk8s.sh --build-images
```

## Uninstallation

### Remove Waddles Only

```bash
# MicroK8s
./install-microk8s.sh --uninstall

# CNCF Kubernetes
./install-k8s.sh --uninstall
```

### Remove Cluster (kind)

```bash
# Remove Waddles and cluster
./install-k8s.sh --kind --uninstall
# When prompted, choose 'y' to delete cluster
```

### Manual Cleanup

```bash
# Delete namespace (removes all resources)
kubectl delete namespace waddlebot

# Or delete specific resources
kubectl delete -k ./k8s/manifests/
```

## Advanced Usage

### Development Workflow

```bash
# 1. Make code changes
vim processing/router_module/app.py

# 2. Rebuild and redeploy
./install-microk8s.sh --build-images

# 3. Watch logs
kubectl logs -n waddlebot deployment/router -f
```

### Scaling Services

```bash
# Scale router
kubectl scale deployment router -n waddlebot --replicas=3

# Scale hub
kubectl scale deployment hub -n waddlebot --replicas=2

# Auto-scaling
kubectl autoscale deployment router -n waddlebot --min=2 --max=5 --cpu-percent=80
```

### Resource Monitoring

```bash
# Resource usage
kubectl top pods -n waddlebot
kubectl top nodes

# Events monitoring
kubectl get events -n waddlebot --watch
```

## Production Deployment

For production deployments, consider:

1. **External Databases**: Use managed PostgreSQL and Redis
2. **TLS/SSL**: Configure cert-manager for HTTPS
3. **Resource Limits**: Adjust CPU/memory based on load
4. **High Availability**: Multiple replicas with pod anti-affinity
5. **Monitoring**: Deploy Prometheus and Grafana
6. **Logging**: Configure centralized logging (ELK, Loki)
7. **Backups**: Automated database backups
8. **Secrets Management**: Use external secrets (Vault, AWS Secrets Manager)
9. **Network Policies**: Restrict pod-to-pod communication
10. **Image Security**: Scan images for vulnerabilities

## Support

For issues or questions:
- **GitHub**: https://github.com/waddlebot/waddles
- **Documentation**: See `/docs/` directory
- **Helm Chart**: See `k8s/helm/waddlebot/README.md`
- **Manifests**: See `k8s/manifests/README.md`

## Files Reference

| File | Description |
|------|-------------|
| `install-microk8s.sh` | MicroK8s installation script |
| `install-k8s.sh` | CNCF Kubernetes installation script |
| `helm/waddlebot/` | Helm chart for Waddles |
| `manifests/` | Raw Kubernetes manifests |
| `INSTALL.md` | This installation guide |

---

**Note:** These installation scripts are designed for local development and testing. For production deployments, review and customize the configuration to meet your security and scalability requirements.
