# GitHub Actions CI/CD for Kubernetes

Complete guide for setting up automated deployment of Waddles to Kubernetes clusters using GitHub Actions.

## Overview

This setup enables automatic deployment of Waddles containers to your Kubernetes cluster whenever you push to the main branch. The workflow:

1. **Builds** all module Docker images
2. **Pushes** images to GitHub Container Registry (GHCR)
3. **Deploys** to your Kubernetes cluster using Helm
4. **Verifies** the deployment and runs smoke tests

## Prerequisites

### Kubernetes Cluster

- **MicroK8s**, **kind**, **minikube**, or any CNCF Kubernetes 1.23+
- Cluster must be accessible from GitHub Actions runners
- For local clusters, use self-hosted GitHub Actions runners

### Required Tools

- kubectl 1.23+
- Helm 3.x
- Cluster admin access (temporary, for initial setup)

## Quick Start

### Step 1: Run Setup Script

Choose the appropriate script for your cluster:

**MicroK8s:**
```bash
cd /home/penguin/code/waddlebot/k8s
./setup-github-actions-microk8s.sh
```

**kind/minikube/other:**
```bash
cd /home/penguin/code/waddlebot/k8s
./setup-github-actions-k8s.sh --kind     # or --minikube
```

The script will:
- Create a service account with namespace-scoped permissions
- Generate a kubeconfig file
- Output GitHub Secrets in copy-paste format

### Step 2: Add Secrets to GitHub

1. Go to your GitHub repository
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add each secret from the setup script output:

| Secret Name | Description |
|-------------|-------------|
| `KUBE_CONFIG_DATA` | Base64-encoded kubeconfig |
| `K8S_NAMESPACE` | Target namespace (default: waddles) |
| `K8S_CLUSTER_ENDPOINT` | API server URL |
| `K8S_CLUSTER_TYPE` | Cluster type (microk8s, kind, minikube) |

### Step 3: Trigger Deployment

```bash
# Push to main branch
git push origin main
```

The GitHub Actions workflow will automatically:
- Build all container images
- Push to GHCR
- Deploy to your Kubernetes cluster

## Architecture

```
┌─────────────────────────────────────────────────┐
│  GitHub Actions Workflow (on push to main)      │
├─────────────────────────────────────────────────┤
│                                                  │
│  Job 1: Build Containers                        │
│  ├─ Build 22 module images                      │
│  ├─ Tag with commit SHA                         │
│  └─ Push to ghcr.io/{owner}/{repo}/{module}     │
│                                                  │
│  Job 2: Deploy to Kubernetes                    │
│  ├─ Wait 30s for GHCR propagation               │
│  ├─ Install kubectl & Helm                      │
│  ├─ Configure kubeconfig                        │
│  ├─ Deploy with Helm                            │
│  ├─ Verify rollout                              │
│  └─ Run smoke tests                             │
│                                                  │
└─────────────────────────────────────────────────┘
```

## How It Works

### 1. Service Account Setup

The setup scripts create a Kubernetes service account with these permissions:

**Namespace-scoped access only** (no cluster-wide permissions):
- Deployments, Services, ConfigMaps, Secrets
- Pods (for logs and health checks)
- PersistentVolumeClaims
- Ingress, Jobs, Events

### 2. Image Registry

**GitHub Container Registry (GHCR):**
- Public or private registry hosted by GitHub
- Automatically authenticated via `GITHUB_TOKEN`
- No additional registry credentials needed
- Images: `ghcr.io/{owner}/{repo}/{module}:{tag}`

### 3. Deployment Process

The workflow uses Helm to deploy:

```bash
helm upgrade --install waddlebot ./k8s/helm/waddlebot \
  --namespace waddlebot \
  --set global.imageRegistry=ghcr.io/owner/repo \
  --set global.imageTag=commit-sha \
  --set global.imagePullPolicy=Always
```

## Configuration

### Custom Namespace

```bash
# Setup script
./setup-github-actions-microk8s.sh --namespace my-namespace

# GitHub Secret
K8S_NAMESPACE=my-namespace
```

### Image Pull Secrets (Private Repositories)

If your GHCR repository is private, GitHub Actions automatically authenticates using `GITHUB_TOKEN`. However, your cluster needs credentials to pull images.

**Create image pull secret:**
```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_PAT \
  --namespace=waddlebot
```

**Update values:**
```yaml
global:
  imagePullSecrets:
    - name: ghcr-secret
```

### Multiple Environments

You can deploy to multiple clusters by:

1. Running setup script for each cluster
2. Creating environment-specific secrets in GitHub
3. Using environment protection rules

## Troubleshooting

### Secrets Not Working

**Issue:** `KUBE_CONFIG_DATA` secret is invalid

**Solution:**
```bash
# Verify the kubeconfig locally
kubectl --kubeconfig=/tmp/github-actions-kubeconfig.yaml get nodes

# Re-encode if needed
cat /tmp/github-actions-kubeconfig.yaml | base64 -w 0
```

### Cluster Not Accessible

**Issue:** GitHub Actions can't reach cluster

**Solutions:**
- **Local clusters:** Use self-hosted GitHub Actions runners
- **Cloud clusters:** Ensure API server is publicly accessible
- **VPN:** Configure GitHub Actions runner with VPN access

### Image Pull Errors

**Issue:** Pods can't pull images from GHCR

**Solution:**
```bash
# Test image pull manually
kubectl run test --image=ghcr.io/owner/repo/module:tag --namespace=waddlebot

# Check events
kubectl get events -n waddlebot --sort-by='.lastTimestamp'

# Create image pull secret (if repo is private)
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=USERNAME \
  --docker-password=PAT \
  -n waddlebot
```

### Deployment Timeout

**Issue:** Deployment takes longer than 15 minutes

**Solution:**
- Check pod logs: `kubectl logs -n waddlebot deployment/router`
- Check resource availability: `kubectl describe pod -n waddlebot POD_NAME`
- Increase timeout in workflow: `--timeout 30m`

### Service Account Permissions

**Issue:** Service account can't create resources

**Solution:**
```bash
# Verify permissions
kubectl --kubeconfig=/tmp/github-actions-kubeconfig.yaml \
  auth can-i create deployments -n waddlebot

# Re-run setup script to recreate role
./setup-github-actions-microk8s.sh
```

## Security Best Practices

### 1. Limit Service Account Permissions

✅ Use namespace-scoped Role (not ClusterRole)
✅ Grant minimum required permissions
✅ Avoid cluster-admin access

### 2. Rotate Secrets Regularly

```bash
# Generate new token
./setup-github-actions-microk8s.sh

# Update KUBE_CONFIG_DATA in GitHub Secrets
```

### 3. Use Environment Protection

GitHub allows environment-specific protection rules:

1. Go to **Settings** > **Environments**
2. Create "production" environment
3. Add required reviewers
4. Modify workflow to use environment

### 4. Audit Deployments

```bash
# View deployment history
kubectl rollout history deployment -n waddlebot

# View events
kubectl get events -n waddlebot --sort-by='.lastTimestamp'
```

## Advanced Usage

### Manual Deployment

Trigger deployment without pushing code:

1. Go to **Actions** tab
2. Select **Waddles CI/CD Pipeline**
3. Click **Run workflow**
4. Select branch and options

### Rollback

```bash
# Using Helm
helm rollback waddlebot -n waddlebot

# Using kubectl
kubectl rollout undo deployment/router -n waddlebot
```

### Deploy Specific Version

Modify workflow to accept version input:

```yaml
workflow_dispatch:
  inputs:
    image_tag:
      description: 'Image tag to deploy'
      required: true
      default: 'latest'
```

### Multi-Cluster Deployment

Use matrix strategy in workflow:

```yaml
strategy:
  matrix:
    cluster: [dev, staging, production]
steps:
  - name: Deploy to ${{ matrix.cluster }}
    run: |
      echo "${{ secrets[format('KUBE_CONFIG_{0}', matrix.cluster)] }}" | base64 -d > ~/.kube/config
      helm upgrade --install ...
```

## Monitoring Deployments

### View Workflow Logs

1. Go to **Actions** tab
2. Click on workflow run
3. View job logs

### Check Cluster Status

```bash
# Get pods
kubectl get pods -n waddlebot

# Get deployments
kubectl get deployments -n waddlebot

# Get services
kubectl get svc -n waddlebot

# View logs
kubectl logs -n waddlebot deployment/router --tail=100 -f
```

### Workflow Badge

Add to README.md:

```markdown
![CI/CD](https://github.com/OWNER/REPO/actions/workflows/ci-cd.yml/badge.svg)
```

## Support

For issues or questions:
- **Setup Script Issues**: Check script output and kubeconfig validity
- **Deployment Issues**: Check GitHub Actions logs and pod logs
- **RBAC Issues**: Verify service account permissions
- **Documentation**: See main [README](README.md) and [INSTALL](INSTALL.md)

## Related Documentation

- [Kubernetes Installation Guide](INSTALL.md)
- [Quick Start Guide](QUICKSTART.md)
- [Helm Chart Documentation](helm/waddlebot/README.md)
- [Raw Manifests](manifests/README.md)
