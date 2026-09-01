# Beta Helm Standardization + Translate Fix

**Date:** 2026-02-19
**Status:** Approved
**Author:** Engineering

---

## Background

The beta cluster (`dal2-beta`, namespace `waddlebot`) accumulated a mixed state: the original Helm deployment (`waddlebot-*` prefixed resources) continued running while a subsequent kustomize apply created a second set of identically-functioned resources with no prefix. This doubled the pod count, exhausted node capacity (110-pod limit on both worker nodes), and left all kustomize pods in Pending state. The `interactive-translate` module was missing from both the Helm chart and the kustomize beta overlay, causing the translation admin page to be non-functional.

---

## Decision: Deployment Tool by Environment

| Environment | Tool | Rationale |
|---|---|---|
| **Beta** (`dal2-beta`) | **Helm** | Release tracking, rollback history, atomic upgrades, values-based config per env |
| **Alpha** (local/minikube) | **Kustomize** | Lightweight, no Helm dependency for local dev, fast iteration |

This is the canonical split going forward. Do not mix tools within an environment.

---

## Scope of Work

### 1. Cluster Cleanup — Delete `waddlebot` Namespace

```bash
kubectl delete namespace waddlebot --context dal2-beta
```

Removes all resources: Helm-managed pods, kustomize-managed pods, PVCs (beta data is disposable), secrets, configmaps, services, ingress. The namespace is recreated by `helm install --create-namespace`.

### 2. Helm Chart — Add `interactive-translate`

Add `k8s/helm/waddlebot/templates/interactive/translate.yaml` modeled on the existing `alias.yaml` pattern, with:
- HTTP port 8033 and gRPC port 50033 (unique to translate)
- `GRPC_PORT` env var
- `MODULE_NAME: interactive-translate`, `MODULE_PORT: 8033`

Add `translate` entry to `values.yaml`:
```yaml
translate:
  enabled: true
  replicas: 1
  resources: <standard interactive resources>
```

Add image override to `values-beta.yaml`:
```yaml
interactive:
  translate:
    image: interactive-translate
```

### 3. Beta Replica Counts

Add `replicas: 1` overrides in `values-beta.yaml` for all interactive, collector, and action modules. Infrastructure (postgres, redis) already defaults to 1. Halves pod footprint, appropriate for beta.

### 4. Kustomize Alpha — Restore `overlays/beta/kustomization.yaml`

The `kustomize edit set image` command during the debugging session reformatted `k8s/kustomize/overlays/beta/kustomization.yaml` and stripped `includeSelectors: false` from the `labels` block. Restore the original clean YAML format with `includeSelectors: false` preserved. The alpha overlay is untouched. `interactive-translate` is already present in the base kustomization from the earlier fix.

### 5. Tooling & Documentation

**`scripts/deploy-beta.sh`:**
- Confirm default `DEPLOY_METHOD="helm"` (already correct)
- Add comment block near the top: *"Deployment tool by environment: Beta = Helm | Alpha/local = Kustomize"*

**`docs/KUBERNETES.md`:**
- Add "Deployment Tool by Environment" section with the table above and rationale

**`deploying-to-beta` skill:**
- Add note that kustomize method is alpha-only; beta exclusively uses Helm

---

## Helm Deploy Command (Beta)

```bash
helm upgrade --install waddlebot k8s/helm/waddlebot \
  --kube-context dal2-beta \
  --namespace waddlebot \
  --create-namespace \
  -f k8s/helm/waddlebot/values.yaml \
  -f k8s/helm/waddlebot/values-beta.yaml \
  --timeout 10m \
  --wait
```

---

## Risks

| Risk | Mitigation |
|---|---|
| Beta downtime during namespace delete | Acceptable — no production load on beta |
| Translate image not in registry at `latest` | Already pushed during debugging session; verify before deploy |
| Other modules missing from Helm chart (clip, lfg, server-status) | Identified during this session — add to Helm chart as part of this work if they have Dockerfiles |

---

## Future Work

- **`scripts/deploy-alpha.sh`** — A kustomize-based counterpart to `deploy-beta.sh` for local/alpha deployments. Not in scope for this session.

---

## Success Criteria

- All pods running with `waddlebot-` prefix (Helm-managed), no unprefixed duplicates
- `waddlebot-interactive-translate` pod Running
- Translation admin page loads config and overlay URL is reachable
- Each module has exactly 1 running pod on beta
- `docs/KUBERNETES.md` documents the Helm/kustomize split
