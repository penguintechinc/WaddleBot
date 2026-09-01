# System Architecture

Waddles runs on a fixed 8-container pipeline (`svc-ingest → svc-process → svc-action →
svc-presentation`, plus `svc-core`, `svc-streaming`, `hub-api`, `hub-webui`), extended by an
**App Bundle marketplace** instead of per-feature containers. This page is a short index — the
canonical, kept-current architecture reference is [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md).

## Design principles

### Fixed pipeline, App Bundle extensibility
Every event flows through the same 4 stages regardless of which App Bundles are activated:
`ingest → process → action → presentation`. A bundle implements 1–4 of those stages; the platform
never grows a new container per feature.

### Event-driven, queue-isolated
Stages communicate over per-`(tenant, community, app_id, stage)` Valkey streams — never a direct
call between stages. A slow `action` handler backs up only its own queue.

### 3-tier lifecycle
`installed` (global) ⊇ `available` (tenant) ⊇ `activated` (community, a set). See
[`docs/ARCHITECTURE.md#app-bundle-model`](../ARCHITECTURE.md#app-bundle-model) for the full
lifecycle and coexistence model.

## The 8 containers

| Container | Responsibility | Language |
|---|---|---|
| `svc-ingest` | Platform receivers + inbound webhooks | Python/Quart |
| `svc-process` | Event bus, command routing, workflow | Python/Quart |
| `svc-action` | Outbound actions + standardized target adapters | Python/Quart |
| `svc-core` | Identity, security, credentials, entitlement (gRPC) | Python/Quart |
| `hub-api` | Admin, tenancy, marketplace, billing, MCP | Python/Quart |
| `hub-webui` | SPA assets, static-serve + `/api` proxy | Node/React |
| `svc-presentation` | Overlays + Music Station | Python/Quart |
| `svc-streaming` | RTC + broadcast media control plane | Python (Rust planned) |

Full per-container port table, build status, and module ownership:
[`docs/ARCHITECTURE.md`](../ARCHITECTURE.md).

## Related pages

- [`core-boundary.md`](core-boundary.md) — per-file evidence for which services are Core vs. Module-owned
- [`database-schema.md`](database-schema.md) — table ownership and schema
- [`event-processing.md`](event-processing.md) — pipeline event flow detail
- [`redis-architecture.md`](redis-architecture.md) — Valkey stream/cache usage
- [`shared-patterns.md`](shared-patterns.md) — cross-service code patterns
- [`table-ownership.md`](table-ownership.md) — which service owns which database table
