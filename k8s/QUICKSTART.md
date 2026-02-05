# Waddles Kubernetes Quick Start

One-page guide to get Waddles running on Kubernetes in minutes.

## Choose Your Platform

### Option 1: MicroK8s (Ubuntu/Debian)

```bash
# Install and deploy in one command
cd /home/penguin/code/waddlebot/k8s
./install-microk8s.sh --build-images
```

**What it does:**
1. Installs MicroK8s if needed
2. Enables required addons (dns, storage, registry, ingress)
3. Builds all Docker images
4. Pushes images to cluster registry
5. Deploys Waddles with Helm
6. Configures access

**Access:** http://waddlebot.local or http://localhost:30080

---

### Option 2: kind (Any Linux)

```bash
# Install and deploy to kind cluster
cd /home/penguin/code/waddlebot/k8s
./install-k8s.sh --kind --build-images
```

**What it does:**
1. Creates kind cluster with ingress support
2. Sets up local registry
3. Builds all Docker images
4. Pushes images to local registry
5. Deploys Waddles with Helm
6. Configures ingress

**Access:** http://waddlebot.local

---

### Option 3: minikube (Any OS)

```bash
# Install and deploy to minikube
cd /home/penguin/code/WaddleBot/k8s
./install-k8s.sh --minikube --build-images
```

**What it does:**
1. Starts minikube cluster
2. Enables addons (ingress, registry, storage)
3. Builds all Docker images
4. Pushes images to minikube registry
5. Deploys Waddles with Helm
6. Configures ingress

**Access:** http://waddlebot.local or `minikube service hub -n waddlebot`

---

## Verification

Check that everything is running:

```bash
# View all pods
kubectl get pods -n waddles

# All pods should show STATUS: Running or Completed
# Example output:
# NAME                              READY   STATUS    RESTARTS   AGE
# postgres-xxxxx                    1/1     Running   0          2m
# redis-xxxxx                       1/1     Running   0          2m
# router-xxxxx                      1/1     Running   0          1m
# hub-xxxxx                         1/1     Running   0          1m
# ...
```

## First Login

1. **Access the Hub UI:**
   - Navigate to http://waddlebot.local
   - Or http://localhost:30080 (MicroK8s NodePort)

2. **Default Credentials:**
   - Username: `admin`
   - Password: `admin` (change immediately!)

3. **Initial Setup:**
   - Create your first community
   - Configure platform integrations (Twitch, Discord, Slack)
   - Set up your first bot commands

## Common Commands

```bash
# View logs
kubectl logs -n waddles deployment/hub -f
kubectl logs -n waddles deployment/router -f

# Restart a service
kubectl rollout restart deployment/hub -n waddles

# Check service status
kubectl get svc -n waddles

# Port forward for direct access
kubectl port-forward -n waddles svc/hub 8060:8060
# Then access: http://localhost:8060
```

## Troubleshooting

### Pods not starting?

```bash
# Check pod details
kubectl describe pod -n waddles <pod-name>

# View pod logs
kubectl logs -n waddles <pod-name>
```

### Can't access waddlebot.local?

Add to `/etc/hosts`:
```bash
echo "127.0.0.1 waddlebot.local" | sudo tee -a /etc/hosts
```

### Images not pulling?

```bash
# MicroK8s: Rebuild images
./install-microk8s.sh --build-images

# kind/minikube: Rebuild images
./install-k8s.sh --kind --build-images  # or --minikube
```

## Uninstall

```bash
# MicroK8s
./install-microk8s.sh --uninstall

# kind
./install-k8s.sh --kind --uninstall

# minikube
./install-k8s.sh --minikube --uninstall
```

## Next Steps

- 📖 [Full Installation Guide](INSTALL.md)
- 🎯 [Helm Chart Documentation](helm/waddlebot/README.md)
- 📝 [Manifest Documentation](manifests/README.md)
- 🛠️ [Development Guide](/docs/development-rules.md)

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────────────────────┐    │
│  │   Ingress    │─────▶│    Hub (Admin Portal)        │    │
│  │  (Nginx)     │      │    Port: 8060                 │    │
│  └──────────────┘      └──────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Core Services                        │   │
│  │  • Router (8000) - Command routing                   │   │
│  │  • Identity (8050) - User management                 │   │
│  │  • Labels (8023) - Label system                      │   │
│  │  • Reputation (8021) - User reputation               │   │
│  │  • Community (8020) - Communities                    │   │
│  │  • Browser Source (8027) - OBS integration           │   │
│  │  • AI Researcher (8070) - Research tools             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Collector Modules (Triggers)             │   │
│  │  • Twitch (8002)     • Discord (8003)                │   │
│  │  • Slack (8004)      • YouTube Live (8006)           │   │
│  │  • Kick (8007)                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Interactive Modules (Actions)              │   │
│  │  • AI (8005)         • Alias (8010)                  │   │
│  │  • Shoutout (8011)   • Inventory (8024)              │   │
│  │  • Calendar (8030)   • Memories (8031)               │   │
│  │  • YouTube Music (8025) • Spotify (8026)             │   │
│  │  • Loyalty (8032)                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Infrastructure                       │   │
│  │  • PostgreSQL (5432) - Database                      │   │
│  │  • Redis (6379) - Cache/sessions                     │   │
│  │  • MinIO (9000/9001) - Object storage                │   │
│  │  • Qdrant (6333) - Vector database                   │   │
│  │  • Ollama (11434) - Local LLM                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Resource Requirements

**Minimum:**
- 8 GB RAM
- 4 CPU cores
- 50 GB disk space

**Recommended:**
- 16 GB RAM
- 8 CPU cores
- 100 GB disk space

## Support

Questions? Issues?
- 📧 GitHub Issues: https://github.com/waddlebot/waddles/issues
- 📚 Documentation: `/docs/` directory
- 💬 Community: (link to Discord/Slack)
