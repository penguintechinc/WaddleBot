# Waddles Kubernetes Deployment

Complete Kubernetes deployment packages for Waddles, including automated installation scripts, Helm charts, and raw manifests.

## 🚀 Quick Start

Choose your platform and run the install script:

### MicroK8s (Ubuntu/Debian)
```bash
./install-microk8s.sh --build-images
```

### kind (Local Development)
```bash
./install-k8s.sh --kind --build-images
```

### minikube
```bash
./install-k8s.sh --minikube --build-images
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed quick start guide.**

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](QUICKSTART.md)** | One-page quick start guide |
| **[INSTALL.md](INSTALL.md)** | Comprehensive installation guide |
| **[GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)** | CI/CD with GitHub Actions setup |
| **[helm/waddlebot/README.md](helm/waddlebot/README.md)** | Helm chart documentation |
| **[manifests/README.md](manifests/README.md)** | Raw manifests documentation |

## 📁 Directory Structure

```
k8s/
├── install-microk8s.sh                  # MicroK8s installation script
├── install-k8s.sh                       # CNCF Kubernetes installation script
├── setup-github-actions-microk8s.sh     # GitHub Actions setup for MicroK8s
├── setup-github-actions-k8s.sh          # GitHub Actions setup for CNCF K8s
├── QUICKSTART.md                        # Quick start guide
├── INSTALL.md                           # Full installation guide
├── GITHUB_ACTIONS.md                    # CI/CD setup guide
├── README.md                            # This file
│
├── helm/                        # Helm Chart
│   └── waddlebot/
│       ├── Chart.yaml           # Helm v3 chart metadata
│       ├── values.yaml          # Default configuration values
│       ├── values-local.yaml    # Local/microk8s overrides
│       ├── README.md            # Helm usage documentation
│       └── templates/           # Kubernetes resource templates
│           ├── _helpers.tpl     # Template helper functions
│           ├── namespace.yaml
│           ├── configmap.yaml
│           ├── secrets.yaml
│           ├── infrastructure/  # 5 infrastructure services
│           ├── core/            # 8 core modules
│           ├── collectors/      # 5 collector modules
│           ├── interactive/     # 9 interactive modules
│           ├── pushing/         # 4 pushing modules
│           └── ingress.yaml
│
└── manifests/                   # Raw Kubernetes Manifests
    ├── kustomization.yaml       # Kustomize configuration
    ├── README.md                # Manifest usage documentation
    ├── namespace.yaml
    ├── configmap.yaml
    ├── secrets.yaml
    ├── infrastructure/          # Infrastructure YAMLs
    ├── core/                    # Core module YAMLs
    ├── collectors/              # Collector YAMLs
    ├── interactive/             # Interactive YAMLs
    ├── pushing/                 # Pushing YAMLs
    └── ingress.yaml
```

## 🎯 Installation Methods

### 1. GitHub Actions CI/CD (Recommended for Production)

Automated deployment triggered by pushing to main branch.

**Setup:**
```bash
# Configure your cluster for GitHub Actions
./setup-github-actions-microk8s.sh  # or setup-github-actions-k8s.sh

# Add secrets to GitHub repository
# See GITHUB_ACTIONS.md for details
```

**Features:**
- Automatic build and push to GHCR on code changes
- Automated deployment to Kubernetes cluster
- Built-in smoke tests and verification
- Rollout status monitoring
- No manual intervention required

**See:** [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) for complete setup guide

### 2. Automated Scripts (Local Development)

Use the installation scripts for local automated deployment:

- **`install-microk8s.sh`** - For MicroK8s clusters
- **`install-k8s.sh`** - For kind, minikube, or any CNCF Kubernetes

**Features:**
- Automatic cluster setup (if using --kind or --minikube)
- Image building and registry push
- Addon enablement (ingress, storage, registry)
- Full deployment with health checks
- Access configuration

### Helm Chart

Use Helm for templated, configurable deployments:

```bash
helm install waddlebot ./helm/waddlebot \
  -f ./helm/waddlebot/values-local.yaml \
  --namespace waddles --create-namespace
```

**Advantages:**
- Template-based configuration
- Easy upgrades and rollbacks
- Release management
- Values file customization

### Raw Manifests

Use kubectl/kustomize for direct manifest deployment:

```bash
kubectl apply -k ./manifests/
```

**Advantages:**
- Simple, transparent YAML
- No Helm dependency
- Direct Kubernetes control
- Easy to version control

## 🛠️ Installation Script Options

### install-microk8s.sh

```bash
./install-microk8s.sh [OPTIONS]

Options:
  --helm              Use Helm chart (default)
  --manifests         Use raw manifests
  --build-images      Build and push images
  --skip-build        Skip image building
  --skip-setup        Skip MicroK8s setup
  --namespace NAME    Custom namespace (default: waddles)
  --uninstall         Uninstall Waddles
  --help              Show help
```

### install-k8s.sh

```bash
./install-k8s.sh [OPTIONS]

Options:
  --helm                Use Helm chart (default)
  --manifests           Use raw manifests
  --build-images        Build and push images
  --skip-build          Skip image building
  --registry URL        Container registry URL
  --context NAME        Kubernetes context
  --namespace NAME      Custom namespace
  --storage-class NAME  StorageClass name
  --ingress-class NAME  IngressClass name
  --kind                Setup kind cluster
  --minikube            Setup minikube cluster
  --uninstall           Uninstall WaddleBot
  --help                Show help
```

## 📦 Components Deployed

### Infrastructure (6 services)
- **PostgreSQL** (5432) - Primary database
- **Redis** (6379) - Cache and session store
- **MinIO** (9000/9001) - Object storage
- **Qdrant** (6333/6334) - Vector database
- **Ollama** (11434) - Local LLM inference
- **OpenWhisk** (3233) - Serverless runtime (optional)

### Core Modules (8 services)
- **Router** (8000) - Command routing and API gateway
- **Hub** (8060) - Admin portal and community management
- **Identity** (8050) - Cross-platform identity linking
- **Labels** (8023) - Label management system
- **Browser Source** (8027/8028) - OBS integration
- **Reputation** (8021) - User reputation tracking
- **Community** (8020) - Community configuration
- **AI Researcher** (8070) - Research and knowledge tools

### Collector Modules (5 services)
- **Twitch** (8002) - Twitch EventSub webhooks
- **Discord** (8003) - Discord bot events
- **Slack** (8004) - Slack events and commands
- **YouTube Live** (8006) - YouTube live chat
- **Kick** (8007) - Kick platform integration

### Interactive Modules (9 services)
- **AI** (8005) - AI-powered interactions
- **Alias** (8010) - Command alias system
- **Shoutout** (8011) - User shoutouts
- **Inventory** (8024) - Inventory management
- **Calendar** (8030) - Event scheduling
- **Memories** (8031) - Community memories
- **YouTube Music** (8025) - YouTube Music integration
- **Spotify** (8026) - Spotify integration
- **Loyalty** (8032) - Loyalty points system

### Pushing Modules (4 services)
- **Discord Action** (8070/50051) - Discord webhooks
- **Slack Action** (8071/50052) - Slack webhooks
- **Twitch Action** (8072/50053) - Twitch actions
- **YouTube Action** (8073/50054) - YouTube actions

**Total: 32 services**

## 🔧 Configuration

### Image Registry

**MicroK8s:**
```bash
# Built-in registry
localhost:32000/waddlebot/
```

**kind:**
```bash
# Local registry container
localhost:5000/waddlebot/
```

**minikube:**
```bash
# Registry addon
localhost:5000/waddlebot/
```

**Custom:**
```bash
# Your registry
./install-k8s.sh --registry gcr.io/my-project/waddlebot
```

### Storage Classes

- **MicroK8s**: `microk8s-hostpath`
- **kind/minikube**: `standard`
- **Custom**: Use `--storage-class` flag

### Ingress Classes

- **MicroK8s**: `public`
- **kind/minikube**: `nginx`
- **Custom**: Use `--ingress-class` flag

## 🌐 Access Methods

### Via Ingress (Recommended)

Add to `/etc/hosts`:
```
127.0.0.1 waddlebot.local
```

Access: **http://waddles.local**

### Via NodePort (MicroK8s)

Direct access: **http://localhost:30080**

### Via Port Forward

```bash
kubectl port-forward -n waddlebot svc/hub 8060:8060
```

Access: **http://localhost:8060**

## 📊 Monitoring

```bash
# View all pods
kubectl get pods -n waddlebot

# Check services
kubectl get svc -n waddlebot

# View logs
kubectl logs -n waddlebot deployment/hub -f
kubectl logs -n waddlebot deployment/router -f

# Check ingress
kubectl get ingress -n waddlebot

# Resource usage
kubectl top pods -n waddlebot
kubectl top nodes
```

## 🔄 Management

### Upgrade

```bash
# Helm
helm upgrade waddlebot ./helm/waddlebot \
  -f ./helm/waddlebot/values-local.yaml \
  -n waddlebot

# Manifests
kubectl apply -k ./manifests/
```

### Scale

```bash
# Scale specific service
kubectl scale deployment router -n waddlebot --replicas=3

# Auto-scale
kubectl autoscale deployment router -n waddlebot \
  --min=2 --max=5 --cpu-percent=80
```

### Restart

```bash
# Restart specific service
kubectl rollout restart deployment/hub -n waddlebot

# Restart all
kubectl rollout restart deployment -n waddlebot
```

### Uninstall

```bash
# MicroK8s
./install-microk8s.sh --uninstall

# CNCF Kubernetes
./install-k8s.sh --uninstall

# Manual
kubectl delete namespace waddlebot
```

## 🐛 Troubleshooting

### Pods Not Starting

```bash
kubectl describe pod -n waddlebot <pod-name>
kubectl logs -n waddlebot <pod-name>
kubectl get events -n waddlebot --sort-by='.lastTimestamp'
```

### Image Pull Errors

```bash
# MicroK8s
microk8s enable registry
curl http://localhost:32000/v2/_catalog

# Rebuild images
./install-microk8s.sh --build-images
```

### Database Issues

```bash
# Check postgres
kubectl get pod -n waddlebot -l app.kubernetes.io/name=postgres

# Test connection
kubectl exec -n waddlebot deployment/router -- \
  python3 -c "import psycopg2; psycopg2.connect('...')"
```

### Storage Issues

```bash
# Check PVCs
kubectl get pvc -n waddlebot
kubectl describe pvc -n waddlebot postgres-pvc

# MicroK8s: Enable storage
microk8s enable storage
```

### Ingress Issues

```bash
# Check ingress
kubectl describe ingress -n waddlebot

# Check controller
kubectl get pods -n ingress-nginx

# MicroK8s: Enable ingress
microk8s enable ingress
```

## ⚙️ Requirements

### Minimum
- **RAM**: 8 GB
- **CPU**: 4 cores
- **Disk**: 50 GB
- **Kubernetes**: 1.23+

### Recommended
- **RAM**: 16 GB
- **CPU**: 8 cores
- **Disk**: 100 GB
- **Kubernetes**: 1.28+

## 🏭 Production Considerations

For production deployments:

1. ✅ Use external managed databases (PostgreSQL, Redis)
2. ✅ Configure TLS/SSL with cert-manager
3. ✅ Adjust resource limits based on actual load
4. ✅ Enable horizontal pod autoscaling
5. ✅ Use proper storage classes (not hostPath)
6. ✅ Implement network policies
7. ✅ Deploy monitoring (Prometheus, Grafana)
8. ✅ Configure logging aggregation (ELK, Loki)
9. ✅ Set up automated database backups
10. ✅ Use external secrets management (Vault, AWS Secrets Manager)

## 📖 Additional Resources

- **Main Documentation**: `/docs/`
- **API Reference**: `/docs/api-reference.md`
- **Database Schema**: `/docs/database-schema.md`
- **Development Guide**: `/docs/development-rules.md`
- **GitHub**: https://github.com/waddlebot/waddles

## 🤝 Support

For issues or questions:
- **GitHub Issues**: https://github.com/waddlebot/waddles/issues
- **Documentation**: See `/docs/` directory
- **Community**: (Discord/Slack links)

## 📄 License

See main project LICENSE file.

---

**Note:** These deployment packages are optimized for local development and testing. Review and customize for production use.
