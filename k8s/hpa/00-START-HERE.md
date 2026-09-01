# START HERE - Waddles Kubernetes HPA Setup

Welcome! This directory contains production-ready Horizontal Pod Autoscaler (HPA) configurations for Waddles. This file will get you started in 5 minutes.

## What is HPA?

Horizontal Pod Autoscaler automatically scales the number of pods based on resource utilization:
- **Scale UP** when load increases (CPU/Memory usage high)
- **Scale DOWN** when load decreases (to save resources)

Example: Your router module automatically scales from 2 to 10 pods during peak hours, then scales back down.

## What's Included (80 KB)

### Configuration Files (3 files)
- `receiver-modules-hpa.yaml` - Auto-scale Twitch, Discord, Slack receivers
- `router-hpa.yaml` - Auto-scale central router
- `action-modules-hpa.yaml` - Auto-scale interactive modules (AI, Alias, etc.)

### Documentation (6 files)
- `README.md` - Complete reference (read for full understanding)
- `DEPLOYMENT_GUIDE.md` - Step-by-step deployment instructions
- `QUICK_REFERENCE.md` - Command cheatsheet
- `INTEGRATION.md` - How HPAs integrate with WaddleBot
- `INDEX.md` - Navigation guide
- `kustomization.yaml` - Kubernetes integration

## Quick Start (5 minutes)

### Step 1: Check Prerequisites (1 minute)

```bash
# Kubernetes cluster running?
kubectl cluster-info

# Metrics Server installed? (required for HPA)
kubectl get deployment metrics-server -n kube-system

# If not found, install it:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Step 2: Deploy HPAs (1 minute)

```bash
# Deploy all HPA configurations
kubectl apply -f k8s/hpa/

# Verify deployment
kubectl get hpa -n waddlebot
```

### Step 3: Verify Status (1 minute)

```bash
# Check HPA status - look for targets like "30%/70%, 20%/80%"
kubectl get hpa -n waddlebot -o wide

# Should show columns: NAME, REFERENCE, TARGETS, MINPODS, MAXPODS, REPLICAS, AGE
```

### Step 4: Done! (2 minutes review)

Your HPAs are now active! Modules will automatically scale based on load.

Watch them in action:
```bash
kubectl get hpa -n waddlebot --watch
```

## Key Scaling Targets

| Component | Min | Max | CPU | Memory |
|-----------|-----|-----|-----|--------|
| Receivers | 2 | 10 | 70% | 80% |
| Router | 2 | 10 | 70% | - |
| Actions | 2 | 8 | 70% | 80% |

All modules scale UP quickly (within 1 minute) and DOWN slowly (5 minute delay).

## What Each File Does

### Configuration Files (YAML)

**receiver-modules-hpa.yaml**
- Auto-scales: Twitch, Discord, Slack receivers
- Range: 2-10 pods each
- Triggers: 70% CPU or 80% memory

**router-hpa.yaml**
- Auto-scales: Central message router
- Range: 2-10 pods
- Trigger: 70% CPU

**action-modules-hpa.yaml**
- Auto-scales: AI, Alias, Shoutout, Inventory, Calendar, Memories, Music, Spotify
- Range: 2-8 pods each
- Triggers: 70% CPU or 80% memory

### Documentation Files (Markdown)

**README.md** (Full Reference)
- Detailed configuration explanations
- Troubleshooting guide (10+ solutions)
- Performance tuning
- Load testing procedures

**DEPLOYMENT_GUIDE.md** (How to Deploy)
- Prerequisites checklist
- 7-step deployment process
- Verification procedures
- Common issues and fixes

**QUICK_REFERENCE.md** (Commands Cheatsheet)
- Deploy command
- Check status commands
- Monitor commands
- Troubleshooting checklist

**INTEGRATION.md** (Technical Details)
- How HPAs fit into WaddleBot
- Compatibility information
- Resource planning
- Migration timeline

**INDEX.md** (Navigation)
- File organization
- Quick navigation by task
- File statistics

## Common Commands

```bash
# Deploy all HPAs
kubectl apply -f k8s/hpa/

# Check status
kubectl get hpa -n waddlebot

# Watch scaling happen
kubectl get hpa -n waddlebot --watch

# Get detailed info on one HPA
kubectl describe hpa router-hpa -n waddlebot

# View scaling events
kubectl get events -n waddlebot --field-selector involvedObject.kind=HorizontalPodAutoscaler

# Delete HPAs (to disable auto-scaling)
kubectl delete hpa -n waddlebot -A
```

## Troubleshooting Checklist

- [ ] Metrics Server running: `kubectl get deployment metrics-server -n kube-system`
- [ ] Metrics available: `kubectl top pods -n waddlebot`
- [ ] HPAs created: `kubectl get hpa -n waddlebot`
- [ ] HPAs showing metrics: `kubectl get hpa -n waddlebot -o wide`
- [ ] Pods have resource requests defined

If any check fails, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) "Common Issues"

## Next Steps

### Immediate (After deployment)
1. Monitor HPA for 30 minutes: `kubectl get hpa -n waddlebot --watch`
2. Verify Metrics available: `kubectl top pods -n waddlebot`
3. Check HPA events: `kubectl describe hpa router-hpa -n waddlebot`

### Today
1. Read [README.md](README.md) for full understanding
2. Review scaling behavior with your team
3. Plan for load testing (optional)

### This Week
1. Run in production for 24-48 hours
2. Monitor scaling patterns
3. Tune parameters if needed (see README.md "Performance Tuning")
4. Document any changes made

### This Month
1. (Optional) Integrate Prometheus for custom metrics
2. Set up alerting for HPA failures
3. Train team on HPA operations

## How Scaling Works

### Scale UP (when busy)
- Every 15 seconds, HPA checks pod metrics
- If CPU > 70% (or Memory > 80%), start scaling up
- Max scaling: Double pods every 30 seconds
- Max waiting: 1 minute before scaling
- Goal: Respond to load spikes quickly

Example: 2 pods → 4 pods → 8 pods (in ~1 minute)

### Scale DOWN (when quiet)
- If CPU < 70% (and Memory < 80%) for 5 minutes, start scaling down
- Remove 1 pod every 60 seconds
- Goal: Save resources, minimize cost
- Conservative to avoid thrashing

Example: 8 pods → 7 pods → 6 pods → ... (over 5+ minutes)

## Real-World Example

Morning traffic spike:
```
9:00 AM - Traffic starts increasing
9:15 AM - CPU reaches 75%, scaling starts: 2 → 4 pods
9:30 AM - Still busy, continues scaling: 4 → 8 pods
9:45 AM - Peak load handled by 8 pods, all CPU ~70%

12:00 PM - Traffic drops
12:05 PM - CPU drops to 40%, scale-down starts
12:10 PM - Removes 1 pod: 8 → 7
12:15 PM - Removes 1 pod: 7 → 6
... continues until back to 2 pods
```

## Important Notes

1. **Metrics Server Required**
   - HPA collects CPU/memory from Metrics Server
   - Must be installed in cluster
   - Takes ~1 minute to report first metrics

2. **Resource Requests Matter**
   - HPA scales based on percentage of resource *requests*
   - All pods must have requests defined (they already do)
   - Don't change resource requests without understanding impact

3. **Min Replicas**
   - All modules have min=2 for redundancy
   - At least 1 pod always available for HA
   - PodDisruptionBudgets prevent all-at-once removal

4. **Cluster Capacity**
   - Ensure cluster has resources for max replicas
   - Max memory needed: ~37GB (all modules at max)
   - Recommend 4-8 nodes for production

## Support & Help

### Quick Questions?
See [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

### How to Deploy?
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

### Something Not Working?
See [README.md](README.md) "Troubleshooting" section

### How Does It Integrate?
See [INTEGRATION.md](INTEGRATION.md)

### File Guide?
See [INDEX.md](INDEX.md)

## File Reading Guide

```
You are here
    ↓
00-START-HERE.md ← Overview (this file)
    ↓
Choose your path:

For deployment:
    ↓
DEPLOYMENT_GUIDE.md ← Step-by-step instructions
    ↓
QUICK_REFERENCE.md ← Commands while deploying

For understanding:
    ↓
README.md ← Complete reference
    ↓
INTEGRATION.md ← How it fits in WaddleBot

For command lookup:
    ↓
QUICK_REFERENCE.md ← Cheatsheet

For navigation:
    ↓
INDEX.md ← File guide
```

## Success Criteria

After deployment, you'll know it's working when:

✓ `kubectl get hpa -n waddlebot` shows all HPAs
✓ HPA status shows metrics (not "unknown")
✓ `kubectl top pods -n waddlebot` shows CPU/memory data
✓ Pod count changes during load
✓ No errors in `kubectl describe hpa`

## Summary

- **What:** Auto-scaling for WaddleBot modules
- **Why:** Handle traffic spikes and save resources
- **When:** Deploy now, monitor today, tune this week
- **How:** Run `kubectl apply -f k8s/hpa/`
- **Help:** See documentation files in this directory

---

## Ready to Deploy?

### Go to: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

### Questions? Start with: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

### Want to understand first? Read: [README.md](README.md)

---

**Last Updated:** 2025-12-09
**Files Created:** 9 (80 KB total)
**Kubernetes:** 1.18+
**Waddles:** 1.0.0+

Happy scaling!
