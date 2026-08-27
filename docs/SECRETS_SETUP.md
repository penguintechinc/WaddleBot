# Secrets Setup Guide

## Alpha (Kustomize)

Generate strong secrets and create a local (gitignored) secretGenerator override:

```bash
JWT_SECRET=$(openssl rand -hex 32)
DB_PASS=$(openssl rand -hex 16)
REDIS_PASS=$(openssl rand -hex 16)
kubectl create secret generic waddlebot-secrets \
  --from-literal=JWT_SECRET="$JWT_SECRET" \
  --from-literal=DATABASE_PASSWORD="$DB_PASS" \
  --from-literal=REDIS_PASSWORD="$REDIS_PASS" \
  --dry-run=client -o yaml > k8s/kustomize/overlays/alpha/secrets-override.yaml
```

## Beta/Prod (Helm)

Use `--set` flags or a local (gitignored) values override, or Sealed Secrets / External Secrets Operator:

```bash
helm upgrade waddlebot ./k8s/helm/waddlebot \
  --set secrets.jwtSecret="$(openssl rand -hex 32)" \
  --set secrets.dbPassword="$(openssl rand -hex 16)"
```

Alternatively, create a `values-secrets.yaml` file (gitignored) with real values and pass it:

```bash
helm upgrade waddlebot ./k8s/helm/waddlebot -f values-secrets.yaml
```
