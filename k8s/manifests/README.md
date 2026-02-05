# Waddles Kubernetes Manifests

Raw Kubernetes manifests for deploying Waddles to a local Kubernetes cluster (microk8s, minikube, kind, etc.).

## Prerequisites

- **kubectl** 1.23+
- **Kubernetes cluster** with:
  - Storage provisioner (hostpath for local)
  - Ingress controller (nginx recommended)
  - At least 8GB RAM, 4 CPU cores
  - 50GB storage available

### For MicroK8s

```bash
# Enable required addons
microk8s enable dns storage registry ingress

# Alias kubectl
alias kubectl='microk8s kubectl'
```

### For Minikube

```bash
# Start with sufficient resources
minikube start --cpus=4 --memory=8192 --disk-size=50g

# Enable ingress
minikube addons enable ingress
```

## Quick Start

### Deploy Everything with Kustomize

```bash
# Apply all manifests
kubectl apply -k /home/penguin/code/waddlebot/k8s/manifests/

# Watch deployment progress
kubectl get pods -n waddlebot -w

# Check service status
kubectl get svc -n waddlebot
```

### Access the Application

Add to `/etc/hosts`:
```
127.0.0.1 waddles.local
```

Access Hub UI:
- **URL**: http://waddles.local (via ingress)
- **Direct**: http://localhost:30080 (NodePort)

## Manual Deployment

If you prefer step-by-step deployment:

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Deploy Configuration

```bash
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
```

### 3. Deploy Infrastructure

```bash
kubectl apply -f infrastructure/postgres.yaml
kubectl apply -f infrastructure/redis.yaml
kubectl apply -f infrastructure/minio.yaml
kubectl apply -f infrastructure/qdrant.yaml
kubectl apply -f infrastructure/ollama.yaml

# Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=infrastructure -n waddlebot --timeout=300s
```

### 4. Deploy Core Modules

```bash
kubectl apply -f core/router.yaml
kubectl apply -f core/hub.yaml
kubectl apply -f core/identity.yaml
kubectl apply -f core/labels.yaml
kubectl apply -f core/browser-source.yaml
kubectl apply -f core/reputation.yaml
kubectl apply -f core/community.yaml
kubectl apply -f core/ai-researcher.yaml

# Wait for core services
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=core -n waddlebot --timeout=300s
```

### 5. Deploy Collectors

```bash
kubectl apply -f collectors/

# Wait for collectors
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=collector -n waddlebot --timeout=180s
```

### 6. Deploy Interactive Modules

```bash
kubectl apply -f interactive/

# Wait for interactive modules
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=interactive -n waddlebot --timeout=180s
```

### 7. Deploy Pushing Modules (Optional)

```bash
kubectl apply -f pushing/
```

### 8. Deploy Ingress

```bash
kubectl apply -f ingress.yaml
```

## Verification

```bash
# Check all pods are running
kubectl get pods -n waddlebot

# Check services
kubectl get svc -n waddlebot

# Check ingress
kubectl get ingress -n waddlebot

# View logs
kubectl logs -n waddlebot deployment/hub --tail=50
kubectl logs -n waddlebot deployment/router --tail=50
```

## Accessing Services

### Via Ingress

```bash
# Hub UI
curl http://waddlebot.local

# Router health check
curl http://waddlebot.local/api/router/health
```

### Via Port Forward

```bash
# Hub
kubectl port-forward -n waddlebot svc/hub 8060:8060

# Router
kubectl port-forward -n waddlebot svc/router 8000:8000

# PostgreSQL
kubectl port-forward -n waddlebot svc/postgres 5432:5432

# Redis
kubectl port-forward -n waddlebot svc/redis 6379:6379
```

## Customization

### Update Secrets

```bash
# Edit secrets
kubectl edit secret waddlebot-secrets -n waddlebot

# Or recreate
kubectl delete secret waddlebot-secrets -n waddlebot
# Edit secrets.yaml with your values
kubectl apply -f secrets.yaml
```

### Update ConfigMap

```bash
# Edit configuration
kubectl edit configmap waddlebot-config -n waddlebot

# Restart pods to pick up changes
kubectl rollout restart deployment -n waddlebot
```

### Scale Services

```bash
# Scale router
kubectl scale deployment router -n waddlebot --replicas=3

# Scale hub
kubectl scale deployment hub -n waddlebot --replicas=2
```

### Update Images

```bash
# Update a specific deployment
kubectl set image deployment/router -n waddlebot \
  router=localhost:32000/waddlebot/router_module_flask:v1.2.0

# Or edit and update tag
kubectl edit deployment router -n waddlebot
```

## Cleanup

### Remove Everything

```bash
# Using kustomize
kubectl delete -k /home/penguin/code/waddlebot/k8s/manifests/

# Or delete namespace (removes all resources)
kubectl delete namespace waddlebot
```

### Remove Specific Components

```bash
# Remove interactive modules only
kubectl delete -f interactive/ -n waddlebot

# Remove infrastructure
kubectl delete -f infrastructure/ -n waddlebot
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n waddlebot

# Check events
kubectl get events -n waddlebot --sort-by='.lastTimestamp'

# View logs
kubectl logs <pod-name> -n waddlebot
```

### Database Connection Issues

```bash
# Check postgres is running
kubectl get pod -l app.kubernetes.io/name=postgres -n waddlebot

# Test connection
kubectl exec -it deployment/router -n waddlebot -- \
  python3 -c "import psycopg2; psycopg2.connect('postgresql://waddlebot:waddlebot_secret@postgres:5432/waddlebot')"
```

### Storage Issues

```bash
# Check PVCs
kubectl get pvc -n waddlebot

# Describe PVC
kubectl describe pvc postgres-pvc -n waddlebot

# For microk8s, ensure storage addon is enabled
microk8s enable storage
```

### Ingress Not Working

```bash
# Check ingress
kubectl describe ingress waddlebot-ingress -n waddlebot

# Check ingress controller
kubectl get pods -n ingress-nginx  # or kube-system for microk8s

# For microk8s
microk8s enable ingress
```

### Image Pull Errors

```bash
# Check if registry is accessible
curl localhost:32000/v2/_catalog

# For microk8s, enable registry
microk8s enable registry

# Push images to registry
docker tag waddlebot/router:latest localhost:32000/waddlebot/router_module_flask:latest
docker push localhost:32000/waddlebot/router_module_flask:latest
```

## Production Considerations

These manifests are configured for **local development** with:
- Small resource limits
- NodePort services
- No TLS/SSL
- Single replicas
- hostPath storage

For production deployment:
1. Use external databases (managed PostgreSQL, Redis)
2. Configure proper resource limits based on load
3. Enable horizontal pod autoscaling
4. Use persistent volume claims with proper storage classes
5. Configure TLS certificates (cert-manager)
6. Implement network policies
7. Configure monitoring (Prometheus, Grafana)
8. Set up logging aggregation (ELK, Loki)
9. Configure backups for databases
10. Use secrets management (External Secrets, Vault)

## Support

For issues or questions:
- GitHub: https://github.com/waddlebot/waddles
- Documentation: See `/home/penguin/code/waddlebot/docs/`
