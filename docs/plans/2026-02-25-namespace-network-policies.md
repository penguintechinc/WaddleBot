# Namespace-Level Network Policies Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Kubernetes NetworkPolicies to the waddlebot namespace that deny all cross-namespace ingress traffic while allowing intra-namespace and ingress-controller traffic.

**Architecture:** Two NetworkPolicies in a single Helm template — a default-deny-ingress baseline, and an allow rule for same-namespace + ingress-nginx. Toggled via existing `networkPolicy.enabled` value. No egress restrictions.

**Tech Stack:** Kubernetes NetworkPolicy API (networking.k8s.io/v1), Helm templating

---

### Task 1: Create the NetworkPolicy Helm template

**Files:**
- Create: `k8s/helm/waddlebot/templates/network-policies.yaml`

**Step 1: Create the template file**

```yaml
{{- if .Values.networkPolicy.enabled }}
# Default deny all ingress traffic from outside the namespace.
# With this policy in place, only explicitly allowed traffic can reach pods.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: {{ .Values.namespace }}
  labels:
    app.kubernetes.io/name: waddlebot
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/managed-by: {{ .Release.Service }}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
# Allow ingress from pods in the same namespace and from the ingress controller namespace.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace-and-ingress
  namespace: {{ .Values.namespace }}
  labels:
    app.kubernetes.io/name: waddlebot
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/managed-by: {{ .Release.Service }}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    # Rule 1: Allow all traffic from pods within the waddlebot namespace
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: {{ .Values.namespace }}
    # Rule 2: Allow traffic from the ingress controller namespace
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: {{ .Values.networkPolicy.ingressNamespace | default "ingress-nginx" }}
{{- end }}
```

**Step 2: Verify template renders correctly**

Run: `helm template waddlebot k8s/helm/waddlebot -f k8s/helm/waddlebot/values.yaml -f k8s/helm/waddlebot/values-beta.yaml --show-only templates/network-policies.yaml`

Expected: Should render the two NetworkPolicy resources with correct namespace values. If `networkPolicy.enabled` is still false in beta, temporarily test with `--set networkPolicy.enabled=true`.

---

### Task 2: Update values.yaml — add ingressNamespace field

**Files:**
- Modify: `k8s/helm/waddlebot/values.yaml:1149-1154`

**Step 1: Add ingressNamespace to the existing networkPolicy section**

Replace lines 1149-1154:
```yaml
# Network Policies
networkPolicy:
  enabled: false
  policyTypes:
    - Ingress
    - Egress
```

With:
```yaml
# Network Policies — namespace-level ingress isolation
# When enabled, denies all cross-namespace ingress and allows only
# same-namespace traffic + ingress controller traffic.
networkPolicy:
  enabled: false
  ingressNamespace: ingress-nginx
```

The old `policyTypes` list is unused (the template hardcodes `Ingress` only). Remove it to avoid confusion.

---

### Task 3: Enable NetworkPolicy in values-beta.yaml

**Files:**
- Modify: `k8s/helm/waddlebot/values-beta.yaml` (append before kong section, ~line 283)

**Step 1: Add networkPolicy override**

Insert after the `tls` / ingress section and before the `# Kong API Gateway` comment (after line 282):

```yaml

# Network Policies — enabled in beta for namespace isolation
networkPolicy:
  enabled: true
```

**Step 2: Verify full template rendering**

Run: `helm template waddlebot k8s/helm/waddlebot -f k8s/helm/waddlebot/values.yaml -f k8s/helm/waddlebot/values-beta.yaml --show-only templates/network-policies.yaml`

Expected: Two NetworkPolicy resources rendered with `namespace: waddlebot`, allowing traffic from `waddlebot` and `ingress-nginx` namespaces.

---

### Task 4: Validate with helm lint

**Step 1: Lint the chart**

Run: `helm lint k8s/helm/waddlebot -f k8s/helm/waddlebot/values.yaml -f k8s/helm/waddlebot/values-beta.yaml`

Expected: No errors. Warnings about missing Chart.yaml fields are acceptable.

**Step 2: Verify disabled state still works**

Run: `helm template waddlebot k8s/helm/waddlebot -f k8s/helm/waddlebot/values.yaml --show-only templates/network-policies.yaml`

Expected: Empty output (no resources rendered when `enabled: false`).

---

### Task 5: Commit

**Step 1: Stage and commit**

```bash
git add k8s/helm/waddlebot/templates/network-policies.yaml \
        k8s/helm/waddlebot/values.yaml \
        k8s/helm/waddlebot/values-beta.yaml \
        docs/plans/2026-02-25-namespace-network-policies-design.md \
        docs/plans/2026-02-25-namespace-network-policies.md
git commit -m "feat(k8s): add namespace-level network policies for ingress isolation

Add default-deny-ingress + allow-same-namespace-and-ingress NetworkPolicies.
Enabled in beta, disabled by default. Blocks cross-namespace lateral movement
while allowing intra-namespace and ingress-controller traffic."
```
