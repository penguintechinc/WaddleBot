# Kong Subchart Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Kong API Gateway as a Helm subchart so it deploys to beta alongside WaddleBot, using the shared Postgres instance with a dedicated `kong` database and user.

**Architecture:** Kong chart `2.52.0` is added as a subchart dependency in `Chart.yaml`, disabled by default, enabled in `values-beta.yaml`. The existing `infra-postgres` init SQL is extended to provision a `kong` DB and user. The hub-api deployment gets `KONG_ADMIN_URL` pointing to `http://kong-admin:8001`.

**Tech Stack:** Helm 4, kong/kong chart 2.52.0, Kong 3.9 (DB-backed mode), PostgreSQL 16

---

### Task 1: Add kong subchart dependency to Chart.yaml

**Files:**
- Modify: `k8s/helm/waddlebot/Chart.yaml`

**Step 1: Add the dependency block**

Open `k8s/helm/waddlebot/Chart.yaml` and append after the `maintainers` block:

```yaml
dependencies:
  - name: kong
    version: "2.52.0"
    repository: "https://charts.konghq.com"
    condition: kong.enabled
```

Final file should look like:
```yaml
apiVersion: v2
name: waddlebot
description: Waddles - Multi-platform chat bot system with microservices architecture
type: application
version: 0.1.0
appVersion: "1.0.0"
kubeVersion: ">=1.23.0-0"
keywords:
  - chatbot
  - twitch
  - discord
  - slack
  - streaming
home: https://github.com/waddlebot/waddlebot
maintainers:
  - name: Waddles Team

dependencies:
  - name: kong
    version: "2.52.0"
    repository: "https://charts.konghq.com"
    condition: kong.enabled
```

**Step 2: Run helm dependency update**

```bash
cd k8s/helm/waddlebot
helm dependency update
```

Expected: Downloads `kong-2.52.0.tgz` into `charts/` directory. You should see:
```
Saving 1 charts
Downloading kong from repo https://charts.konghq.com
Deleting outdated charts
```

**Step 3: Verify chart downloaded**

```bash
ls k8s/helm/waddlebot/charts/
```

Expected: `kong-2.52.0.tgz`

**Step 4: Commit**

```bash
git add k8s/helm/waddlebot/Chart.yaml k8s/helm/waddlebot/Chart.lock k8s/helm/waddlebot/charts/
git commit -m "feat(helm): add kong/kong 2.52.0 as subchart dependency"
```

---

### Task 2: Add Kong Postgres credentials to secrets and configmap

**Files:**
- Read first: `k8s/helm/waddlebot/templates/secrets.yaml`
- Read first: `k8s/helm/waddlebot/templates/configmap.yaml`
- Modify: `k8s/helm/waddlebot/templates/secrets.yaml`
- Modify: `k8s/helm/waddlebot/templates/configmap.yaml`
- Modify: `k8s/helm/waddlebot/values.yaml`

**Step 1: Read current secrets.yaml to understand the pattern**

Read `k8s/helm/waddlebot/templates/secrets.yaml` — find where `POSTGRES_PASSWORD` is defined and add `KONG_PG_PASSWORD` in the same style immediately after it.

Add to the `data:` block of `waddlebot-secrets`:
```yaml
  KONG_PG_PASSWORD: {{ .Values.infrastructure.postgresql.kongPassword | b64enc | quote }}
```

**Step 2: Read current configmap.yaml to understand the pattern**

Read `k8s/helm/waddlebot/templates/configmap.yaml` — find where `POSTGRES_USER` / `POSTGRES_DB` are defined and add Kong DB config in the same style.

Add to the `data:` block of `waddlebot-config`:
```yaml
  KONG_PG_USER: {{ .Values.infrastructure.postgresql.kongUser | quote }}
  KONG_PG_DATABASE: {{ .Values.infrastructure.postgresql.kongDatabase | quote }}
```

**Step 3: Add defaults to values.yaml**

Read `k8s/helm/waddlebot/values.yaml`, find the `infrastructure.postgresql` section. Add these three fields:

```yaml
    kongUser: "kong"
    kongDatabase: "kong"
    kongPassword: "changeme_kong_pg"
```

**Step 4: Lint to verify no template errors**

```bash
helm lint k8s/helm/waddlebot --set kong.enabled=false
```

Expected: `1 chart(s) linted, 0 chart(s) failed`

**Step 5: Commit**

```bash
git add k8s/helm/waddlebot/templates/secrets.yaml k8s/helm/waddlebot/templates/configmap.yaml k8s/helm/waddlebot/values.yaml
git commit -m "feat(helm): add Kong Postgres credentials to secrets/configmap/values"
```

---

### Task 3: Extend Postgres init SQL to provision Kong DB and user

**Files:**
- Modify: `k8s/helm/waddlebot/templates/infrastructure/postgres.yaml`

**Step 1: Find the init SQL section**

Read `k8s/helm/waddlebot/templates/infrastructure/postgres.yaml`. Locate the `postgres-init-script` ConfigMap's `init.sql` data block — it ends with `GRANT ALL PRIVILEGES ON SCHEMA community`.

**Step 2: Append Kong provisioning SQL**

Add the following immediately after the last `GRANT` line in the init SQL (still inside the `init.sql: |` block, maintaining 4-space indentation):

```sql
    -- Kong API Gateway database and user
    CREATE USER {{ "{{" }} .Values.infrastructure.postgresql.kongUser {{ "}}" }} WITH PASSWORD '{{ "{{" }} .Values.infrastructure.postgresql.kongPassword {{ "}}" }}';
    CREATE DATABASE {{ "{{" }} .Values.infrastructure.postgresql.kongDatabase {{ "}}" }} OWNER {{ "{{" }} .Values.infrastructure.postgresql.kongUser {{ "}}" }};
    GRANT ALL PRIVILEGES ON DATABASE {{ "{{" }} .Values.infrastructure.postgresql.kongDatabase {{ "}}" }} TO {{ "{{" }} .Values.infrastructure.postgresql.kongUser {{ "}}" }};
```

Note: In the actual file these are real Go template expressions (no escaping needed), written as:
```
    CREATE USER {{ .Values.infrastructure.postgresql.kongUser }} WITH PASSWORD '{{ .Values.infrastructure.postgresql.kongPassword }}';
    CREATE DATABASE {{ .Values.infrastructure.postgresql.kongDatabase }} OWNER {{ .Values.infrastructure.postgresql.kongUser }};
    GRANT ALL PRIVILEGES ON DATABASE {{ .Values.infrastructure.postgresql.kongDatabase }} TO {{ .Values.infrastructure.postgresql.kongUser }};
```

**Step 3: Lint**

```bash
helm lint k8s/helm/waddlebot --set kong.enabled=false
```

Expected: `1 chart(s) linted, 0 chart(s) failed`

**Step 4: Commit**

```bash
git add k8s/helm/waddlebot/templates/infrastructure/postgres.yaml
git commit -m "feat(helm): provision Kong DB and user in Postgres init SQL"
```

---

### Task 4: Add Kong subchart values block to values.yaml

**Files:**
- Modify: `k8s/helm/waddlebot/values.yaml`

**Step 1: Append Kong subchart config to the end of values.yaml**

Add this block at the bottom of `k8s/helm/waddlebot/values.yaml`:

```yaml
# Kong API Gateway subchart configuration
# https://github.com/Kong/charts/tree/main/charts/kong
kong:
  enabled: true

  fullnameOverride: kong

  # DB-backed mode using shared infra-postgres
  env:
    database: postgres
    pg_host: infra-postgres
    pg_port: "5432"
    pg_database:
      valueFrom:
        configMapKeyRef:
          name: waddlebot-config
          key: KONG_PG_DATABASE
    pg_user:
      valueFrom:
        configMapKeyRef:
          name: waddlebot-config
          key: KONG_PG_USER
    pg_password:
      valueFrom:
        secretKeyRef:
          name: waddlebot-secrets
          key: KONG_PG_PASSWORD

  # Run migrations automatically on upgrade
  migrations:
    preUpgrade: true
    postUpgrade: true

  # Admin API only — no proxy (WaddleBot uses nginx ingress directly)
  proxy:
    enabled: false

  admin:
    enabled: true
    http:
      enabled: true
      servicePort: 8001
      containerPort: 8001
    tls:
      enabled: false

  # Disable Kong Ingress Controller — we use nginx
  ingressController:
    enabled: false

  # Minimal resources for beta
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

**Step 2: Lint**

```bash
helm lint k8s/helm/waddlebot --set kong.enabled=false
```

Expected: `1 chart(s) linted, 0 chart(s) failed`

**Step 3: Lint with kong enabled (dry-run template render)**

```bash
helm template waddlebot k8s/helm/waddlebot -f k8s/helm/waddlebot/values.yaml -f k8s/helm/waddlebot/values-beta.yaml --set kong.enabled=true 2>&1 | grep -E "Error|error|kong" | head -20
```

Expected: Kong-related resource names printed, no errors.

**Step 4: Commit**

```bash
git add k8s/helm/waddlebot/values.yaml
git commit -m "feat(helm): add kong subchart values block (disabled by default)"
```

---

### Task 5: Enable Kong in values-beta.yaml

**Files:**
- Modify: `k8s/helm/waddlebot/values-beta.yaml`

**Step 1: Add kong enable block to values-beta.yaml**

Open `k8s/helm/waddlebot/values-beta.yaml`. After the `infrastructure:` block (around line 30), add:

```yaml
# Kong API Gateway - enabled in beta
kong:
  enabled: true
```

**Step 2: Verify full template render with beta values**

```bash
helm template waddlebot k8s/helm/waddlebot \
  -f k8s/helm/waddlebot/values.yaml \
  -f k8s/helm/waddlebot/values-beta.yaml 2>&1 | grep -E "^kind:|name: kong" | head -20
```

Expected: Should show `kind: Deployment`, `kind: Service` etc. for `kong-admin` service.

**Step 3: Confirm admin service name**

```bash
helm template waddlebot k8s/helm/waddlebot \
  -f k8s/helm/waddlebot/values.yaml \
  -f k8s/helm/waddlebot/values-beta.yaml 2>&1 | grep "name: kong-admin"
```

Expected: `name: kong-admin` appears in a Service resource.

**Step 4: Commit**

```bash
git add k8s/helm/waddlebot/values-beta.yaml
git commit -m "feat(helm): enable Kong subchart in beta values"
```

---

### Task 6: Wire KONG_ADMIN_URL into hub-api deployment

**Files:**
- Modify: `k8s/helm/waddlebot/templates/core/hub.yaml`

**Step 1: Read hub.yaml to find the env block**

Read `k8s/helm/waddlebot/templates/core/hub.yaml`. Find the `env:` block inside the hub container spec (around line 48). It currently has `MODULE_NAME` and `MODULE_PORT`.

**Step 2: Add KONG_ADMIN_URL env var**

After `MODULE_PORT`, add:

```yaml
        - name: KONG_ADMIN_URL
          value: "http://kong-admin:8001"
```

**Step 3: Lint**

```bash
helm lint k8s/helm/waddlebot -f k8s/helm/waddlebot/values-beta.yaml
```

Expected: `1 chart(s) linted, 0 chart(s) failed`

**Step 4: Verify env var appears in rendered template**

```bash
helm template waddlebot k8s/helm/waddlebot \
  -f k8s/helm/waddlebot/values.yaml \
  -f k8s/helm/waddlebot/values-beta.yaml 2>&1 | grep -A2 "KONG_ADMIN_URL"
```

Expected:
```
- name: KONG_ADMIN_URL
  value: http://kong-admin:8001
```

**Step 5: Commit**

```bash
git add k8s/helm/waddlebot/templates/core/hub.yaml
git commit -m "feat(helm): set KONG_ADMIN_URL env var in hub-api deployment"
```

---

### Task 7: Deploy to beta and verify Kong comes up

**Step 1: Run deploy script (skip hub image rebuild — only Helm changes)**

```bash
TAG=beta-1771946287 ./scripts/deploy-beta.sh --skip-build 2>&1
```

Note: This will fail at `--wait` due to pre-existing unhealthy pods in the cluster — that is expected and known. The important signal is whether the script errors before reaching the Helm step.

**Step 2: Check Kong pods come up**

```bash
kubectl --context dal2-beta get pods -n waddlebot | grep kong
```

Expected: A `kong-*` pod progressing through `Init` (running migrations) then `Running`.

Wait up to 3 minutes for migrations to complete — Kong bootstraps its schema on first run, which takes ~30 seconds.

**Step 3: Verify Kong admin API is reachable from within cluster**

```bash
kubectl --context dal2-beta exec -n waddlebot \
  $(kubectl --context dal2-beta get pod -n waddlebot -l app.kubernetes.io/name=hub -o jsonpath='{.items[0].metadata.name}') \
  -- curl -s http://kong-admin:8001/status | head -c 200
```

Expected: JSON response with Kong version and status info.

**Step 4: Verify hub-api Kong health endpoint**

```bash
curl -sk -H "Host: waddlebot.penguintech.cloud" \
  https://dal2.penguintech.io/api/superadmin/kong/health
```

Expected: HTTP 200 with `{ "status": "healthy" }` or similar — no more `ENOTFOUND kong` errors in hub-api logs.

**Step 5: Check hub-api logs for Kong errors**

```bash
kubectl --context dal2-beta logs -n waddlebot \
  $(kubectl --context dal2-beta get pod -n waddlebot -l app.kubernetes.io/name=hub -o jsonpath='{.items[0].metadata.name}') \
  --tail=30 2>&1 | grep -i kong
```

Expected: No `ENOTFOUND kong` or connection refused errors.

**Step 6: Commit deploy script fix (--force-conflicts)**

The `--force-conflicts` flag was already added to `scripts/deploy-beta.sh` earlier in this session. Make sure that change is staged:

```bash
git add scripts/deploy-beta.sh
git commit -m "fix(deploy): add --force-conflicts to helm upgrade for SSA field manager conflicts"
```
