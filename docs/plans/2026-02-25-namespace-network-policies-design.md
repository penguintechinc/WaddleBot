# Namespace-Level Network Policy Design

**Date**: 2026-02-25
**Status**: Approved
**Scope**: dal2 beta cluster, `waddlebot` namespace

## Problem

The WaddleBot Kubernetes deployment has no NetworkPolicies. All pods can communicate freely across namespaces, which means a compromised pod in any namespace could access WaddleBot services (PostgreSQL, Redis, internal APIs).

## Decision

Implement **namespace-level ingress isolation**: deny all inbound traffic by default, then allow traffic only from within the `waddlebot` namespace and from the `ingress-nginx` namespace.

## Design

### Two NetworkPolicies

**1. `default-deny-ingress`**
- Selects all pods (empty `podSelector: {}`)
- `policyTypes: [Ingress]` with no ingress rules = deny all inbound
- This is the baseline that flips the namespace from open to closed

**2. `allow-same-namespace-and-ingress`**
- Selects all pods (empty `podSelector: {}`)
- Allows ingress from:
  - Pods in the same namespace (label: `kubernetes.io/metadata.name: waddlebot`)
  - Pods in the ingress controller namespace (label: `kubernetes.io/metadata.name: ingress-nginx`)
- `policyTypes: [Ingress]` only — no egress restrictions

### Traffic Matrix

| Source | Destination | Allowed? |
|---|---|---|
| waddlebot pod | waddlebot pod | Yes |
| ingress-nginx pod | waddlebot pod | Yes |
| Other namespace pod | waddlebot pod | **Blocked** |
| waddlebot pod | External internet | Yes (no egress restriction) |

### Helm Integration

- **Template file**: `k8s/helm/waddlebot/templates/network-policies.yaml`
- **Toggle**: `networkPolicy.enabled` (existing field in values.yaml)
- **Configurable ingress namespace**: `networkPolicy.ingressNamespace` (default: `ingress-nginx`)
- **Enabled in**: `values-beta.yaml` (set `networkPolicy.enabled: true`)
- **Disabled in**: `values-local.yaml` (remains `false` for local dev)

### Values Schema Update

```yaml
# values.yaml (update existing section)
networkPolicy:
  enabled: false
  ingressNamespace: ingress-nginx

# values-beta.yaml (add)
networkPolicy:
  enabled: true
```

## What This Does NOT Cover

- **Intra-namespace isolation**: All waddlebot pods can still talk to each other freely. This is intentional — the service mesh is complex (~50 pods) and tier-based isolation can be added later.
- **Egress restrictions**: Outbound traffic is unrestricted. Many services need external API access (Discord, Twitch, Slack, YouTube, Spotify, Kick APIs).
- **Other namespaces**: No policies applied outside `waddlebot`. Only the waddlebot namespace gets hardened.

## CNI Prerequisite

NetworkPolicies require a CNI that enforces them. Calico and Cilium support them; Flannel alone does not. The dal2 cluster CNI should be verified before enabling.

## Rollback

Set `networkPolicy.enabled: false` in values-beta.yaml and redeploy. Policies are removed, traffic returns to default allow-all.
