# HPA Integration with Waddles

This document describes how HPA configurations integrate with Waddles's Kubernetes deployment.

## Directory Structure

```
k8s/
├── hpa/                              # HPA Configurations (NEW)
│   ├── receiver-modules-hpa.yaml    # Receiver module HPAs
│   ├── router-hpa.yaml              # Router HPA
│   ├── action-modules-hpa.yaml      # Action module HPAs
│   ├── kustomization.yaml           # HPA Kustomization
│   ├── README.md                    # Full documentation
│   ├── DEPLOYMENT_GUIDE.md          # Step-by-step guide
│   ├── QUICK_REFERENCE.md           # Quick reference
│   └── INTEGRATION.md               # This file
├── manifests/                       # Existing deployments
│   ├── collectors/                  # Receiver modules
│   ├── core/                        # Core modules (router, etc.)
│   ├── interactive/                 # Action modules
│   ├── pushing/                     # Pushing modules
│   ├── infrastructure/              # Infrastructure
│   └── kustomization.yaml
└── helm/                            # Helm charts
```

## HPA Naming Convention

HPA names follow the pattern: `{deployment-name}-hpa`

### Receiver Module HPAs
- `twitch-collector-hpa` → targets `Deployment/twitch-collector`
- `discord-collector-hpa` → targets `Deployment/discord-collector`
- `slack-collector-hpa` → targets `Deployment/slack-collector`

### Router Module HPA
- `router-hpa` → targets `Deployment/router`

### Action Module HPAs
- `ai-interaction-hpa` → targets `Deployment/ai-interaction`
- `alias-interaction-hpa` → targets `Deployment/alias-interaction`
- `shoutout-interaction-hpa` → targets `Deployment/shoutout-interaction`
- `inventory-interaction-hpa` → targets `Deployment/inventory-interaction`
- `calendar-interaction-hpa` → targets `Deployment/calendar-interaction`
- `memories-interaction-hpa` → targets `Deployment/memories-interaction`
- `youtube-music-interaction-hpa` → targets `Deployment/youtube-music-interaction`
- `spotify-interaction-hpa` → targets `Deployment/spotify-interaction`

## Integration with Existing Deployments

HPA works with existing WaddleBot deployments without modification:

### Compatible Deployments
All deployments in `/home/penguin/code/waddlebot/k8s/manifests/` are compatible:

✓ **Receiver Modules** (`collectors/`)
  - `twitch.yaml` - Twitch EventSub collector
  - `discord.yaml` - Discord event collector
  - `slack.yaml` - Slack event collector

✓ **Processing** (`core/router.yaml`)
  - Router module with rolling update strategy

✓ **Action Modules** (`interactive/`)
  - `ai.yaml` - AI interaction
  - `alias.yaml` - Alias commands
  - `shoutout.yaml` - Shoutout module
  - `inventory.yaml` - Inventory management
  - `calendar.yaml` - Calendar management
  - `memories.yaml` - Memory management
  - `youtube-music.yaml` - YouTube Music integration
  - `spotify.yaml` - Spotify integration

### Required Features in Deployments
For HPA to work, deployments must have:

1. **Resource Requests**
   ```yaml
   resources:
     requests:
       cpu: 100m        # Required for CPU-based scaling
       memory: 256Mi    # Required for memory-based scaling
   ```

2. **Health Checks** (for availability)
   ```yaml
   livenessProbe:
     httpGet:
       path: /health
       port: 8002
   readinessProbe:
     httpGet:
       path: /health
   ```

3. **Rolling Update Strategy** (for graceful scaling)
   ```yaml
   strategy:
     type: RollingUpdate
     rollingUpdate:
       maxSurge: 1
       maxUnavailable: 0
   ```

All WaddleBot deployments already have these features.

## Kustomization Integration

### Method 1: Include HPAs in Main Kustomization

Edit `/home/penguin/code/waddlebot/k8s/manifests/kustomization.yaml`:

```yaml
resources:
- namespace.yaml
- configmap.yaml
- secrets.yaml
- ingress.yaml
- collectors/
- core/
- interactive/
- pushing/
- infrastructure/
- ../hpa/                    # Add this line
```

Then apply:
```bash
kubectl apply -k k8s/manifests/
```

### Method 2: Apply HPAs Separately

Keep HPAs separate from main Kustomization:

```bash
# Apply main infrastructure
kubectl apply -k k8s/manifests/

# Apply HPAs separately
kubectl apply -f k8s/hpa/
```

### Method 3: Use HPA Kustomization

The `/home/penguin/code/waddlebot/k8s/hpa/kustomization.yaml` can be applied independently:

```bash
kubectl apply -k k8s/hpa/
```

## Upgrade Considerations

### Upgrading from Static Replicas to HPA

If deployments currently have static `replicas: N`:

1. **Before applying HPA:**
   - Review current replica counts
   - Document current scaling patterns
   - Plan for different min/max values if needed

2. **Apply HPAs:**
   - HPA will manage replica count
   - Initial replicas field becomes "advisory"
   - HPA takes over scaling decisions

3. **After HPA deployment:**
   - Monitor scaling behavior
   - Verify Metrics Server collecting data
   - Adjust targets if needed

### Rolling Back from HPA

To remove HPAs and return to static replicas:

```bash
# Delete HPAs
kubectl delete hpa -n waddlebot -A

# Manually set replica counts
kubectl scale deployment router -n waddlebot --replicas=2
kubectl scale deployment ai-interaction -n waddlebot --replicas=2
# ... etc for all deployments
```

## Monitoring Integration

### Metrics Collection

HPAs use Kubernetes Metrics Server to collect:

```
Metrics Server (kubelet)
    ↓
HPA Controller (every 15s)
    ↓
Scaling Decisions
```

### Logging Scaling Events

HPA creates Kubernetes events for scaling:

```bash
# View HPA scaling events
kubectl describe hpa router-hpa -n waddlebot

# View all HPA events
kubectl get events -n waddlebot --field-selector involvedObject.kind=HorizontalPodAutoscaler

# Watch in real-time
kubectl get events -n waddlebot -w --field-selector involvedObject.kind=HorizontalPodAutoscaler
```

### Custom Metrics (Future)

For advanced scaling based on custom metrics (request rate, latency, queue depth):

1. Install Prometheus
2. Configure metrics collection
3. Deploy Prometheus Adapter
4. Add custom metrics to HPAs

See `README.md` section "Performance Tuning" for details.

## Resource Planning

### Cluster Capacity

Ensure cluster has resources for max replica counts:

```
Total Capacity = Sum of (max replicas × resource limit) for all modules

Example calculation:
- Receivers: 3 × 10 × 512Mi = 15Gi
- Router: 1 × 10 × 1Gi = 10Gi
- Actions: 8 × 8 × 512Mi = 32Gi
Total: ~57Gi memory (plus CPU)
```

### Node Sizing

For efficient packing:

```bash
# Current setup (2 receiver + 2 router + 2×8 action = ~30 pods)
# Each pod: ~512Mi memory

# At max scaling (10+10+8×8 = ~74 pods)
# Estimate: 74 pods × 512Mi = 37Gi memory needed

# Recommendation: 4-8 nodes with 4Gi+ memory each
```

## Best Practices

### 1. Resource Requests Must Be Accurate
```yaml
# DON'T: Set too high (wastes resources)
resources:
  requests:
    cpu: 1000m
    memory: 4Gi

# DO: Set realistic minimums
resources:
  requests:
    cpu: 100m      # Actual average usage
    memory: 256Mi  # Realistic baseline
```

### 2. Monitor During Peak Hours
```bash
# Schedule monitoring during expected peak load
kubectl get hpa -n waddlebot --watch
kubectl top pods -n waddlebot
```

### 3. Document Changes
When tuning HPA parameters, document:
- Why you changed the value
- What behavior you observed
- What results you achieved
- Date of change

### 4. Test in Staging First
```bash
# Deploy to staging environment
kubectl apply -f k8s/hpa/ -n waddlebot-staging

# Load test and monitor
# Review scaling patterns
# Adjust if needed
# Deploy to production
```

### 5. Coordinate with Team
- Brief team on HPA behavior
- Explain how to monitor scaling
- Document troubleshooting steps
- Set up alerts for failed scaling

## Troubleshooting Integration Issues

### HPAs created but not scaling

**Check:**
1. Metrics available: `kubectl top pods -n waddlebot`
2. HPA targeting correct deployment: `kubectl describe hpa router-hpa -n waddlebot`
3. Utilization threshold: `kubectl get hpa router-hpa -n waddlebot -o wide`

### Pods pending after scaling

**Check:**
1. Node resources: `kubectl describe nodes`
2. Pod resource requests: `kubectl describe pod <pod-name> -n waddlebot`
3. Cluster capacity: `kubectl top nodes`

### Deployment replicas not matching HPA

**Check:**
1. Let HPA settle for 1 minute
2. View HPA status: `kubectl describe hpa router-hpa -n waddlebot`
3. Check for pod disruption budgets: `kubectl get pdb -n waddlebot`

## Performance Impact

### Expected Changes
- **Memory**: Slight increase (~1-2%) for HPA controller
- **CPU**: Minimal (~10 millicores) for metrics collection
- **API Calls**: ~1 additional call per pod per 15 seconds

### Expected Benefits
- **High Load Response**: 2-3x faster response during surges
- **Cost Efficiency**: Automatic scale-down saves resources during low load
- **Availability**: Better distribution of load across pods

## Compatibility Matrix

| Component | Version | Supported |
|-----------|---------|-----------|
| Kubernetes | 1.18+ | ✓ |
| Metrics Server | 0.4.0+ | ✓ |
| WaddleBot | 1.0.0+ | ✓ |
| Kustomize | 3.0+ | ✓ |
| Docker | 19.0+ | ✓ |

## Migration Timeline

### Phase 1: Preparation (Week 1)
- Review HPA documentation
- Plan resource requirements
- Deploy to staging environment

### Phase 2: Testing (Week 2)
- Load test in staging
- Monitor scaling patterns
- Tune parameters if needed

### Phase 3: Staging Validation (Week 3)
- Run HPAs in staging for 1 week
- Monitor stability
- Get team approval

### Phase 4: Production Deployment (Week 4)
- Deploy HPAs to production
- Monitor first 48 hours intensively
- Adjust based on observations

## Support & Escalation

### Issues to escalate:
- Persistent HPA scaling failures
- Pods consistently pending after scaling
- Metrics not available for >5 minutes
- Unexpected scaling behavior

### Resources:
- HPA Documentation: `k8s/hpa/README.md`
- Quick Reference: `k8s/hpa/QUICK_REFERENCE.md`
- Kubernetes Docs: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

---

**Last Updated:** 2025-12-09
**Waddles Version:** 1.0.0+
**Kubernetes Version:** 1.18+
