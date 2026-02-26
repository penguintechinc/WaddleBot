# Kong Subchart Integration Design

**Date:** 2026-02-24
**Status:** Approved
**Branch:** rebrand/waddlebot-to-waddles

## Goal

Add Kong API Gateway as a Helm subchart dependency so it is deployed to the beta cluster alongside WaddleBot. The hub-api superadmin panel manages Kong via its Admin API (`/superadmin/kong/*` routes).

## Architecture

Kong runs in **DB-backed mode** using the existing shared `infra-postgres` instance with a dedicated `kong` database and `kong` user. The Kong subchart is disabled by default and enabled in `values-beta.yaml`.

```
hub-api  -->  http://kong-admin:8001  (Kong Admin API)
             kong (subchart)
             └── infra-postgres:5432/kong  (shared Postgres, dedicated DB/user)
```

## Components

### 1. `Chart.yaml`
Add `kong/kong` chart `2.52.0` as a subchart dependency with `condition: kong.enabled`.

### 2. `templates/infrastructure/postgres.yaml` — init SQL extension
Add SQL to the existing init ConfigMap to:
- Create a `kong` database
- Create a `kong` user with password from `{{ .Values.infrastructure.postgresql.kongPassword }}`
- Grant `kong` user full privileges on the `kong` database

### 3. `templates/secrets.yaml`
Add `KONG_PG_PASSWORD` key sourced from `values.infrastructure.postgresql.kongPassword`.

### 4. `values.yaml`
- Add `infrastructure.postgresql.kongPassword` field (default `changeme_kong_pg`)
- Add `kong:` subchart block, `enabled: false`, configure:
  - `fullnameOverride: kong` → makes admin service DNS name `kong-admin`
  - `env.database: postgres`
  - `env.pg_host: infra-postgres`
  - `env.pg_port: "5432"`
  - `env.pg_database: kong`
  - `env.pg_user: kong`
  - `env.pg_password.valueFrom.secretKeyRef` → `waddlebot-secrets / KONG_PG_PASSWORD`
  - `ingressController.enabled: false` (we use nginx ingress, not KIC)
  - `proxy.enabled: false` (no proxy needed — hub only talks to Admin API)
  - `admin.enabled: true`, `admin.http.enabled: true`
  - `migrations.enabled: true` (runs `kong migrations bootstrap` as init job)

### 5. `values-beta.yaml`
Add `kong.enabled: true`.

### 6. `templates/core/hub.yaml`
Add `KONG_ADMIN_URL` env var to the hub container:
```yaml
- name: KONG_ADMIN_URL
  value: "http://kong-admin:8001"
```

## Service Naming

`fullnameOverride: kong` causes the Kong subchart to name its services:
- Admin API → `kong-admin:8001`
- Proxy (disabled) → not created

The hub-api `KONG_ADMIN_URL` env var is set to `http://kong-admin:8001` directly in the hub deployment template.

## Notes

- Kong 3.x chart (`3.0.x`) has breaking subchart value restructuring; using `2.52.0` for stability
- `proxy.enabled: false` — WaddleBot uses nginx ingress directly, not Kong as a proxy
- The Postgres init SQL uses `IF NOT EXISTS` guards so it is idempotent on re-runs
