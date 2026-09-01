# Waddles Deployment Guide

Production-hardening reference for a Waddles deployment. For the fastest path to a running
instance, start with the [Quick Start Guide](../QUICKSTART.md) — this page covers the additional
choices you need for a real production rollout: secrets, monitoring, network policy, scaling, and
backups.

**Kubernetes via Helm is the only supported deployment path** — alpha through production. Docker
Compose (`docker-compose.yml` at the repo root) exists for local development only and is not a
supported production deployment method.

## Prerequisites

- Kubernetes cluster 1.24+, 3+ nodes for production
- `kubectl` and `Helm 3`
- PostgreSQL 14+ (managed service recommended for production)
- Redis/Valkey 6+
- A secrets mechanism: Vault, Sealed Secrets, or External Secrets Operator
- Container images from `ghcr.io/penguintechinc/waddlebot/*` (beta/gamma/prod tags are CI-built —
  never build production images locally)

## Values Files

The chart at `k8s/helm/waddlebot/` ships one values file per environment:

| File | Environment |
|---|---|
| `values-local.yaml` | Local Kubernetes (MicroK8s, Docker Desktop) |
| `values-alpha.yaml` | Alpha |
| `values-beta.yaml` | Beta (`dal2-beta` context) |
| `values.yaml` | Chart defaults — do not deploy directly; override per environment |

Deploy and upgrade commands are in [`QUICKSTART.md`](../QUICKSTART.md#deploy-with-helm).

## Secrets

Never put real credentials in a values file or commit them. Supply secrets (database password,
JWT signing key, platform OAuth credentials) through your cluster's secrets mechanism and
reference them from `k8s/helm/waddlebot/templates/secrets.yaml`. See
[`docs/SECRETS_SETUP.md`](../SECRETS_SETUP.md) for the concrete setup and
[`docs/CREDENTIALS-ROTATION-CHECKLIST.md`](../CREDENTIALS-ROTATION-CHECKLIST.md) for rotation
procedures.

## Autoscaling

Each service in the chart has its own `autoscaling` block in `values.yaml` (`enabled`,
`minReplicas`, `maxReplicas`, `targetCPUUtilizationPercentage`) rendered to a
`HorizontalPodAutoscaler` per Deployment — there is no separate autoscaling manifest to apply.
Tune per service under `values-{env}.yaml` before rollout; the shared `values.yaml` defaults are
conservative starting points, not production sizing.

## Network Policy

`networkPolicy.enabled` (default `false` in `values.yaml`) turns on namespace-scoped ingress
isolation — same-namespace traffic and the configured `ingressNamespace` are allowed, everything
else is denied. Enable it per environment in `values-{env}.yaml`; see
[`docs/architecture/core-boundary.md`](../architecture/core-boundary.md) for the service
communication map it needs to allow.

## Monitoring

`monitoring.prometheus.enabled` and `monitoring.grafana.enabled` (both default `false`) add a
`ServiceMonitor`/dashboard hook for an existing Prometheus Operator / Grafana install — the chart
does not deploy Prometheus or Grafana itself. Point them at your own monitoring stack.

## SPIFFE/SPIRE

`spire.enabled` (default `false`) opts into the bundled `charts/spire` subchart for
mTLS workload identity. See that subchart's own values and README for the trust-domain/topology
options before enabling it in a shared environment.

## Backups

Automate PostgreSQL backups against whichever Postgres you point the chart at (managed service
snapshot/PITR for beta+/production, or `pg_dump` on a schedule for smaller deployments) — see
[`docs/DATABASE.md`](../DATABASE.md) for schema and per-service account layout. There is no
bundled backup CronJob in the chart today; treat backups as an operational responsibility of
whoever runs the Postgres instance.

## Troubleshooting

```bash
# Pod not starting
kubectl --context <ctx> logs -n waddlebot deploy/<name> --previous
kubectl --context <ctx> describe pod -n waddlebot <pod-name>

# Service discovery / DNS
kubectl --context <ctx> get endpoints -n waddlebot
kubectl --context <ctx> exec -n waddlebot deploy/<name> -- nslookup <other-service>

# Database connectivity
kubectl --context <ctx> logs -n waddlebot deploy/waddlebot-postgres
```

## Next Steps

- [Architecture](../ARCHITECTURE.md) — the 8-container pipeline and App Bundle model
- [Kubernetes](../KUBERNETES.md) — Helm chart reference
- [Secrets Setup](../SECRETS_SETUP.md)
- [Database](../DATABASE.md)
