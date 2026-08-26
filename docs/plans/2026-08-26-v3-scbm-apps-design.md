# v3.0.x SCBM Module + App Architecture Design

**Date:** 2026-08-26
**Status:** Draft
**Branch:** docs/v3-scbm-architecture

## Goal

Restructure Waddles from a flat collection of ~40 co-equal service containers into a
layered platform: a mandatory **Core**, four globally-toggleable **Modules** (Social,
Customer, Bot, Marketing), **Features** that Modules group, and **Apps** that implement
those Features and can be swapped per tenant or per community through the marketplace.

Deployment collapses to **seven containers** along an ingest → process → action pipeline.
The logical hierarchy and the container topology are deliberately independent — conflating
them is what produced the ~40.

The model is Nextcloud's: a core platform plus an app store, where the shipped defaults
are themselves apps. Nothing is a privileged built-in, because a built-in that cannot be
replaced makes the extension point decorative.

v3.0.0 ships **feature parity with v2.2.x** — Social and Bot fully populated — plus
lightweight Customer and Marketing. It does not attempt a complete CRM or a full
conferencing suite; those are 3.x work with their own specs.

## Hierarchy

```
Core / shared services      identity · event bus · marketplace · tenancy · workflow
        │                   always on, every deployment
        ▼
Module                      Social · Customer · Bot · Marketing
        │                   ON/OFF GLOBALLY (cluster-wide) — the key differentiator
        ▼
Feature                     social.polls · bot.shoutout · customer.pipeline
        │                   a versioned contract; gated by license tier AND PostHog flag
        ▼
App                         first-party default │ marketplace alternative
                            the implementation; bound per tenant and/or community
```

The scoping ladder narrows at each level, and each level uses a different mechanism:

| Level | Enable/disable scope | Mechanism | Who decides |
|-------|---------------------|-----------|-------------|
| Core | always on | mandatory dependency | nobody — it is not optional |
| Module | global / cluster-wide | values flag; pipeline containers load its App bundles | cluster operator |
| Feature | per tenant | license tier × PostHog flag | licensing + rollout |
| App | per tenant and/or community | marketplace binding | tenant admin / community admin |

A Module is either on or off for the whole cluster. There is deliberately no per-tenant
Module toggle: per-tenant variation belongs one level down, at Features, where it costs a
flag lookup rather than a deployment topology.

Note that "off" means its Apps are not loaded, not that a pod disappears — containers are
organised by role rather than by Module. See Deployment.

## Identity and data scoping

Identity, authorization, and data containerization all follow one ladder:

```
global  →  tenant  →  community
                      (surfaces as "team" or "org" in some Modules)
```

Each level carries its own scopes. **Roles are bundles of scopes at a level**, expanded at
token issuance; middleware checks scopes only, never role names. Narrower levels restrict
what a broader level granted — they never expand it.

| Level | Boundary | Example scopes |
|-------|----------|----------------|
| Global | the platform | `*:admin`, `platform:read` |
| Tenant | the customer; always present on every token | `community:create`, `billing:read` |
| Community | a team/org inside a tenant | `social.polls:write`, `bot.command:admin` |

Per `security.md`: every token carries a `tenant` claim, tenant middleware runs *before*
scope checks, a mismatch is an immediate 403, and every query, cache key and service call
is scoped to the token's tenant **at the ORM layer** — never from a request body or
parameter. Data containerization follows the same three levels, so a community's data is
addressable only through its tenant.

**Everything today lives in the default tenant, and continues to.** The default tenant is a
tenant like any other, not a bypass — the same claim, the same middleware, the same key
namespace. That is what keeps the migration non-breaking while preventing an untenanted code
path surviving as a backdoor.

It is also the **permanent** shape for most deployments, not a migration artifact: Free and
Professional are both capped at the single default tenant, and only Enterprise is
multi-tenant. That cuts both ways and is worth being deliberate about:

- The single-tenant path is the *common* path, so it must not be the slow or awkward one.
- The multi-tenant path is exercised only by Enterprise deployments, so it will rot unless
  the single-tenant case runs the identical code with N=1. A `if tenant == "default": ...`
  shortcut would leave the multi-tenant branch effectively untested in most environments.

### Consequences for Features and Apps

- A Feature contract declares the scopes it requires. An App implementing that Feature
  **inherits those scopes and cannot widen them** — installing a third-party App must never
  be a privilege-escalation path.
- Third-party App execution is already tenant-scoped through the marketplace; per-community
  binding narrows it further, and the executing identity is the community's, not the
  vendor's.

### What exists today

The ladder is **half-built**, and the half that is missing is the enforcing half:

| Piece | State |
|-------|-------|
| `tenants`, `tenant_admins`, `tenant_settings` tables | exist |
| `communities.tenant_id` FK | exists |
| Hub (Node) tenant resolution + `is_global` | exists — `middleware/auth.js` sets `req.tenant` |
| Python service fleet | **tenant-blind** — 246 files query by `community_id` with no tenant filter |
| Roles as per-level scope bundles | **not implemented** — `flask_core.setup_default_roles` defines four global roles, and `admin` holds `['*']` |

The Python services reach communities directly by `community_id` without checking that the
community belongs to the caller's tenant. `security.md` names the equivalent pattern as
forbidden: a query without a tenant filter in a multi-tenant system is a tenant-isolation
hole regardless of whether the id arrives in a body, a param, or a path.

Closing this is P0 work and the largest single item in it — 246 files plus a middleware
layer plus the role model. It is not v3 scope creep; every Feature and App gating decision
downstream assumes a trustworthy tenant claim, so nothing above it is sound until it lands.

### This ladder is parallel to App binding, not the same as it

Identity has a **global** level. App binding deliberately does not — the shipped default
App is code, not a bindable row, so there is no cluster-wide replacement. An operator can
hold global admin scope and still not swap a community's App platform-wide.

The two ladders look alike and must not be collapsed into one mechanism: one answers *who
may act on what*, the other answers *which implementation serves this slot here*.

## Service identity: SPIFFE/SPIRE

User identity answers *who is acting*. Service identity answers *which workload is calling*.
Both are required; neither substitutes for the other.

Every pod gets an X.509-SVID from a SPIRE agent over the Workload API. SPIFFE IDs follow
the house pattern from `penguintech.md`:

```
spiffe://penguintech.io/{env}/{service}
```

Collapsing to seven containers makes this tractable: seven registration entries per
environment instead of forty.

### Two deployment modes, one values flip apart

SkausWatch is itself a modular platform, and its **authentication module** provides this —
`skauswatch-auth` (JWT claims and scope authz), `skauswatch-identity` (SPIFFE Workload API),
`skauswatch-spire-entry`, plus the `spire`, `pki`, `sshca` and `vault` charts. The
`skauswatch-spire` chart is a nested SPIFFE/SPIRE trust authority for the single
`penguintech.io` trust domain: root plus per-cluster child servers.

That module has already solved this problem in Rust. Waddles is Python, so it mirrors the
shape rather than reusing the crates:

| Mode | Configuration | When |
|------|---------------|------|
| **Independent** | `topology.role: child`, `topology.upstreamRoot.enabled: false` | a standalone Waddles deployment; the child runs its own self-signed CA |
| **Centralized** | `topology.role: child`, `topology.upstreamRoot.enabled: true` | nested under an external root such as SkausWatch, sharing the `penguintech.io` trust domain |

Deploy as `child` with the upstream disabled, **not** as `standalone`. The chart is written
so a child promotes to nested mode without a `topology.role` change — it needs only a join
token and the root's trust bundle. Choosing `standalone` would buy nothing now and force a
topology change to federate later.

### How it composes with the rest of this design

SPIFFE is one of three identity mechanisms here, and they answer different questions:

| Mechanism | Answers | Scope |
|-----------|---------|-------|
| X.509-SVID | which *workload* is calling | per service |
| Machine JWT | what that call is *allowed to do* | per service, scoped |
| Valkey ACL user | which *tenant's* data it may touch | per (tenant, stage) |

An SVID does not carry tenancy, so it complements the per-tenant ACL users rather than
replacing them. A compromised stage still authenticates as itself; what the tenant ACL
constrains is which keys it can reach.

#### Holding an SVID is not checking one

`skauswatch-identity` splits this into two responsibilities, and the second is the one easy
to omit:

- `IdentityProvider` attests to the local Workload API socket (`SPIFFE_ENDPOINT_SOCKET`),
  holds the X.509-SVID and trust bundle set, and builds mTLS configs from them.
- `SpiffeIdMatcher` is a **caller-supplied allowlist enforced against the peer's SPIFFE ID**,
  and is what admits federated trust domains.

Presenting an identity and verifying the other end's are different things. Without the
matcher, mTLS proves only that the peer holds *some* valid SVID in the trust domain — every
workload in the mesh would pass. Each of the seven services declares which peer SPIFFE IDs
it accepts; `svc-core` accepting calls from the three stages is not the same as accepting
calls from anything holding a `penguintech.io` SVID.

Per `security.md`, mTLS does **not** remove the JWT requirement: every inter-service call
carries a short-lived signed JWT regardless of transport, whether or not SPIFFE is live for
that call. The two remaining call shapes after consolidation:

- **stage → `svc-core` gRPC** — mTLS with SVIDs, plus the machine JWT.
- **stage → Valkey** — Valkey speaks TLS with client certificates, so the SVID can
  authenticate the connection while the per-tenant ACL user authorizes the keyspace.

Being SPIFFE-*ready* is the requirement even where SPIRE is not deployed: services accept an
mTLS/X.509-SVID identity as a first-class mechanism, so enabling SPIRE in an environment is
configuration rather than a rewrite. Nothing in waddlebot implements this today — the
codebase has zero SPIFFE references outside standards documents.

## Vocabulary

The word "module" currently means three different things in this repo, which is why the
existing `services/` consolidation is hard to reason about:

- a deployable container — `core/identity_core_module/`
- a marketplace-installable unit — `hub_module_installations.module_id`
- a Python package — `action/interactive/*_module/`

v3 splits these:

| Term | Means | Example |
|------|-------|---------|
| **Core** | the mandatory platform | identity, event bus, marketplace |
| **Module** | one of four product surfaces, a grouping of Features | Social, Customer, Bot, Marketing |
| **Feature** | a versioned capability contract inside a Module | `bot.shoutout`, `social.polls` |
| **App** | an implementation of a Feature, installable and bindable | `shoutout-default`, `acme-shoutout-pro` |
| **Service** | a deployable container, a pipeline stage or a supporting role | `svc-ingest`, `svc-process` |

Renaming `hub_module_installations` to `app_installations` is part of P1. The existing
column meaning does not change; only the name stops lying.

## Core

Core is everything two or more Modules need. That is the whole test — if a second Module
needs it, it belongs in Core, and if only one does, it does not.

| Core service | Seeded from | Responsibility |
|--------------|-------------|----------------|
| identity | `core/identity_core_module` | OIDC/JWT, tenant claim, scopes |
| security | `core/security_core_module` | authz enforcement, audit |
| credentials | `core/credential_manager_module` | per-tenant secret custody |
| tenancy | `core/community_module` | tenants, communities, membership |
| event bus | `flask_core.stream_pipeline`, consolidated | **a shared library over Valkey Streams, not a service** — see Transport |
| workflow | `core/workflow_core_module` | cross-Module automation |
| analytics | `core/analytics_core_module` | shared telemetry sink |
| marketplace | `admin/marketplace_module` | catalog, vendors, subscriptions, App installs + bindings |
| hub | `admin/hub_module` | admin shell that mounts enabled Modules |
| entitlement client | new, wraps `penguin-licensing` + PostHog | the Feature gate |

### The router split

`processing/router_module` today mixes two concerns: generic event routing, and
Twitch/Discord command semantics (command registry, cooldowns, emote handling).

The generic half becomes the Core **event bus** — which is a *library*, not a service. It is
the consolidated `StreamPipeline` that every stage links against to publish and consume on
Valkey Streams. Putting a gRPC service in front of Valkey would add a hop and a failure
domain to buy nothing; the stream broker is already the shared component.

The command half stays in Bot, as a consumer of `waddles:t:{tenant}:process`.

Without this split, Social, Customer and Marketing would each have to depend on Bot to emit
an event — which would make the Modules interdependent and defeat global toggling.

## Modules

Modules never import each other. Cross-Module behaviour goes through the Core event bus.
This is what makes "deploy Bot only" or "Social + Customer" a values-file decision rather
than a fork.

| Module | Scope | Seeded from | Green-field share |
|--------|-------|-------------|-------------------|
| **Bot** | triggers, actions, interactions, command dispatch | `trigger/receiver/*`, `action/pushing/*`, `action/interactive/*` | ~0% — this is v2.2.x |
| **Social** | chat, presence, communities, voice/video, browser sources | `community_module`, `presence`, `alias`, `quote`, `shoutout`, `module_rtc`, `video_proxy`, `browser_source_core` | ~50% |
| **Marketing** | scheduling, publishing, cross-platform analytics | `engagement_module`, part of `analytics_core` | ~70% |
| **Customer** | accounts, contacts, opportunities, pipelines, cases | nothing | ~100% |

Social's ambition (replace Slack/Discord *and* Zoom/Teams) and Customer's (SuiteCRM/Odoo
class) are each multi-year products. This design covers how they plug in, not what they
contain. Each gets its own spec.

## Features

A Feature is a **contract**, not code. It declares:

- a stable id — `social.polls`
- a versioned interface — the API an App must satisfy
- the Core capabilities an implementing App may use
- the minimum license tier
- a PostHog flag key — `waddles.social.polls`

Because a community can swap in a third-party App, the Feature interface is the load-
bearing boundary in this architecture — more so than Module boundaries, which are only
deployment groupings. Feature interfaces get semantic versioning and a deprecation window;
Module boundaries do not need one.

### Gating

A Feature is available to a tenant when **both** hold:

1. the tenant's license tier entitles it, and
2. its PostHog flag evaluates true for that tenant.

New flags default OFF. If either the license server or PostHog is unreachable, fall back
to the last-known cached value; never crash, and never fail open on a never-seen flag.

#### Middleware ordering is a contract, not a preference

`skauswatch-auth` states it explicitly, and v3 adopts the same ordering:

```
tenant check  →  scope check  →  feature / licensing check
```

The order is load-bearing in both directions:

- **Tenant before scope.** A scope check against an unverified tenant answers the wrong
  question — it establishes what the caller may do, without establishing whose data they are
  doing it to. `security.md` requires tenant middleware to run first for exactly this reason.
- **Scope before feature.** A feature gate consulted before authorization leaks entitlement
  information to callers who have no business asking, and burns a licensing round-trip on
  requests that were going to 403 anyway.

Authorization decisions use `scope` only. `roles` is informational and audit-only and is
never branched on — roles are bundles expanded into scopes at token issuance.

This mirrors the WaddleAI product definition in `license-server` — see
`api/app/seeds/waddleai.py`, where each feature carries `tier_requirements` per tier plus
`default_entitled`. v3 adds `api/app/seeds/waddles.py` in the same shape.

## Apps

An App implements one or more Features. **First-party defaults are Apps too** — shipping in
the box is a default *binding*, not a different kind of code. This is the only way the
extension point is real rather than nominal.

### Manifest

```yaml
id: shoutout-default
module: bot
stages: [process, action]       # which pipeline containers load it
provides: [bot.shoutout@1]      # Feature contracts, versioned
requires_core: [identity, event-bus, tenancy]
requires_scopes: [bot.command:write]
min_tier: free
flag: waddles.bot.shoutout
vendor: penguintech             # first-party
```

`stages` is what lets a container decide, at load time, whether an App is its concern.
A first-party App may span stages; a third-party App never does — it is reached over the
network from whichever stage invokes it, so its manifest declares the calling stage only.

### Binding resolution

Narrowest scope wins:

```
community binding  →  tenant binding  →  shipped default App
```

Two Apps claiming the same Feature is not a conflict; the binding at that scope picks one.
The first-party App remains a permanent fallback and **cannot be swapped cluster-wide** —
there is deliberately no platform-scope binding. That guarantees every deployment has a
known-good baseline to compare against when a third-party App misbehaves, which is what
makes support tractable.

### Two entitlement systems

These are separate and both already half-exist:

| | First-party Feature | Third-party App |
|---|---|---|
| Gate | license tier + PostHog flag | marketplace subscription |
| Lives in | `license-server` `tier_requirements` | `marketplace_module` `subscriptionController` |
| Scope | per tenant | per tenant/community install |

A third-party App may implement a Feature the tenant's tier does not entitle. The Feature
gate wins: buying an App does not buy the Feature slot it plugs into.

### Third-party Apps never run in our process

A third-party App is always reached across a network boundary, in one of exactly two
shapes. Both are already implemented in `vendorExecutionService.executeCommand()`:

| Model | Direction | Transport | Auth |
|-------|-----------|-----------|------|
| `webhook_push` | we call out to them | POST to the App's `webhook_url`, response is the result | HMAC-SHA256 over the payload, `webhook_secret` |
| `rest_pull` | our API to their API | POST to `api_base_url + /execute` | `api_key` bearer, `oauth2_client_credentials` bearer, or HMAC fallback via `X-WaddleBot-Signature` |

`webhook_push` covers external ecosystems and serverless targets — Lambda, GCP Functions,
OpenWhisk, or any vendor endpoint. `rest_pull` covers standing third-party integrations
with their own API surface.

We never execute vendor code in-process, and vendors never execute ours. Three consequences
worth stating, because they shape decisions elsewhere in this design:

- **Container consolidation is safe.** Collapsing first-party services into seven role
  containers puts no untrusted code in a shared process, because untrusted code was never
  in-process to begin with.
- **Every third-party App is a network hop**, so a Feature served by one inherits a timeout
  and a failure mode a first-party App does not. Feature contracts must therefore specify
  timeout and fallback behaviour, not just a signature — `webhook_timeout_ms` already
  exists per module and defaults to 5000ms.
- **Egress is a policy surface.** Per `security.md`, outbound is deny-by-default with an
  allowlist; each installed App's endpoint becomes an allowlist entry scoped to the
  installing tenant, not a blanket open egress.

### What already exists

More of this is built than the naming suggests:

- `hub_module_installations (community_id, module_id)` is the App-installation table.
- `routerIntegrationController.getCommunityCommands(communityId)` already resolves
  per-community marketplace units at runtime.
- `vendorExecutionService.executeCommand()` already executes third-party code.

v3 generalises this from "commands" to Feature contracts, and inserts the **tenant** scope
between community and default.

## Deployment

**Container topology is a packaging decision, deliberately decoupled from the logical
model.** Modules, Features and Apps are code and configuration; they do not each get a pod.
v2.2.x's ~40 co-equal containers are the cost of having conflated the two.

The spine is a **pipeline**, which is already the shape of the system — `trigger/receiver`
→ `processing/router` → `action/*` — just spread across forty containers instead of three:

```
        ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
inbound │  svc-ingest  │ ───▶ │ svc-process  │ ───▶ │  svc-action  │ outbound
        └──────────────┘      └──────────────┘      └──────────────┘
         platform events       event bus, routing,    actions, interactions,
         + webhooks            command dispatch,      third-party App calls
                               workflow
```

Each stage scales on a different axis, which is the reason they are separate and the test
for whether a future split is justified:

| Container | Carries | Scales on |
|-----------|---------|-----------|
| `svc-ingest` | platform receivers (Twitch, Discord, Slack, Teams, YouTube, Kick, GoogleChat, Mattermost), inbound webhooks | count of long-lived inbound connections |
| `svc-process` | Core event bus, routing, Bot command dispatch, workflow | event volume |
| `svc-action` | outbound actions, interaction Apps, third-party App calls | outbound throughput and remote latency |

### Transport between stages: Valkey Streams

The stages are joined by **Valkey Streams consumer groups**, not by synchronous calls.
This is what makes the pipeline a pipeline rather than three services phoning each other:

```
svc-ingest ──XADD──▶ waddles:t:{tenant}:ingest ──XREADGROUP──▶ svc-process
                                                                    │
                                              XADD ────────────────┘
                                                ▼
                              waddles:t:{tenant}:action ──XREADGROUP──▶ svc-action
                                                                            │
                                  poison ────XADD───▶ waddles:t:{tenant}:dlq
```

Streams are per tenant — see Tenant isolation below.

What consumer groups buy, all of which the current point-to-point design lacks:

| Property | Consequence |
|----------|-------------|
| Backpressure | a slow `svc-action` queues rather than timing out `svc-ingest` |
| At-least-once + ack | a crashed consumer's in-flight events are redelivered, not lost |
| Horizontal scale per stage | replicas join one group and split the partition — this is *why* stages scale independently |
| Replay | a stream is a log; a bad deploy can be reprocessed from an offset |
| DLQ | poison events are parked, not retried forever |

#### Most of the gRPC mesh disappears

The existing gRPC surface — 21 client call sites, a port registry, per-module `.proto`
files — exists because two dozen containers had to talk to each other. It is a *symptom* of
the container sprawl, not an independent design choice, and collapsing to seven removes
most of what it was solving:

| Call shape today | After consolidation |
|------------------|---------------------|
| module → module inside the same stage | **an in-process function call** — no network, no proto, no port |
| stage → stage (event path) | a Valkey Stream |
| stage → `svc-core` (entitlement, identity) | **stays gRPC** — genuinely cross-container and synchronous |

`backend.md` mandates gRPC for service-to-service communication, and that still holds for
the third row. The first row simply stops being service-to-service, so the mandate no longer
applies to it — this is a reduction in surface, not an exception to the rule.

The rule of thumb for what remains: if the caller does not need the result to continue, it
belongs on a stream; if it does and the callee is in another container, gRPC; if it does and
the callee is in the same container, call it.

At-least-once delivery means **consumers must be idempotent**. Every event envelope carries
an id, and consumers dedupe on it. This is not optional — it is the cost of the redelivery
guarantee above, and getting it wrong produces duplicate posts and double-charged actions.

#### Tenant isolation inside Valkey

Tenancy is a segment of the key, not a field in the payload. **Every key carries its tenant**,
and the default tenant is simply one of them:

```
waddles:t:{tenant}:{concern}:...        keys, cache, sessions, rate limits
waddles:t:{tenant}:{stage}              streams — ingest · process · action · dlq
```

Everything today lives in the default tenant and continues to, so the migration is a rename
rather than a re-partition: `waddlebot:cache:*` becomes `waddles:t:default:cache:*`. The
default tenant is not a special case in the code — it is a tenant like any other, which is
what stops the untenanted path from surviving as a backdoor.

**Streams are per tenant.** A shared stream would let every stage consumer read every
tenant's events, which would defeat the key-level isolation entirely — the ACL below would
guard the cache while the event path leaked. This supersedes a shared-stream design: the
cost is real (see limits) but a transport that ignores the tenant boundary is not worth the
saving.

##### ACL users

`docs/architecture/redis-architecture.md` already specifies per-service ACL users
(`cache_user`, `ratelimit_user`, `queue_user`) with key-prefix patterns. It is marked
"Advanced - Optional" and implemented nowhere. v3 implements it and composes it with
tenancy — a user per **(tenant, stage)**:

```
ACL SETUSER waddles-t-{tenant}-ingest on >{secret} \
    ~waddles:t:{tenant}:* +@read +@write +@stream -@dangerous
```

Stages are few, so user count is tenants × ~4 rather than tenants × services. Credentials
live in `credential_manager_module` and rotate there.

**What this actually buys**, stated precisely so it is not oversold: a stage container still
holds credentials for every tenant it serves, so this is not a containment boundary against
a compromised stage. What it is, is **defense in depth against our own bugs** — a connection
authenticated as tenant A cannot read tenant B's keys, so a tenant-scoping mistake surfaces
as a Valkey `NOPERM` error instead of a silent cross-tenant read. That is the exact
datastore-level mirror of the ORM-layer tenant scoping in P0, and the two fail independently.

##### Limits, and where this stops working

Per-tenant separation has a cost that scales with the tenant roster:

| Quantity | Grows as |
|----------|----------|
| Streams | tenants × 4 stages |
| ACL users | tenants × 4 stages |
| Connections | tenants × stages × replicas |

Connections are the binding constraint. Pool per tenant with idle eviction, and keep an
active-tenant set so a stage maintains readers only for tenants with traffic. This holds
comfortably into the hundreds of tenants and needs revisiting in the low thousands.

**In practice this curve only applies to Enterprise.** Free and Professional are capped at the
single default tenant, so their multipliers are all 1 — four streams, four ACL users, one
connection pool. The isolation machinery is built for Enterprise and exercised everywhere at
N=1, which is exactly the property that keeps the multi-tenant path from rotting.

The escape hatch at that point is not to abandon isolation but to shard it: Valkey Cluster
with per-tenant hash tags, or a dedicated Valkey for a large tenant. Dedicated infrastructure
per tenant also maps naturally onto the Enterprise tier if it becomes a commercial line.

#### What exists today

`flask_core.stream_pipeline.StreamPipeline` already implements this — `XADD`,
`XREADGROUP`, `XGROUP CREATE`, acking, and a DLQ. It is used by **exactly one service**
(`processing/router_module`), behind an off-by-default flag. There is also a second,
overlapping implementation in `flask_core.message_queue.MessageQueue`.

So the capability is built and unused. v3's work is adoption and consolidation, not
invention: pick one abstraction, delete the other, and make it the default path between
stages rather than an opt-in extra.

The infrastructure is also still Redis, and Alpine, and unpinned. Eight manifest entries
break the base-image rules — `redis:7-alpine` (4) and `postgres:15/16-alpine` (4) — against
three standing requirements: Valkey over Redis, Debian bookworm over Alpine, and SHA256
digest pinning. Postgres is also split across two majors (15 and 16) with no digest on any
of them.

Correcting all eight to `valkey/valkey:8-bookworm@sha256:<digest>` and
`postgres:17-bookworm@sha256:<digest>` is P0 work.

### Modules cut across stages

A Module is a **vertical**; the pipeline is **horizontal**. A Module is not assigned to a
stage — it contributes code to however many stages it needs, from one to all three:

| Module | `svc-ingest` | `svc-process` | `svc-action` | also |
|--------|-------------|---------------|--------------|------|
| **Bot** | platform receivers | command dispatch, cooldowns | outbound actions, interactions | — |
| **Social** | chat/presence inbound | presence fan-out, routing | chat outbound, browser sources | `svc-rtc` |
| **Marketing** | platform analytics webhooks | scheduling | publishing to X/FB/IG | — |
| **Customer** | — | pipeline automation | notifications | mostly `hub-api` CRUD |

Three consequences:

- **"Module off" is a per-stage operation.** Disabling Social means not loading its bundles
  in ingest *and* process *and* action, and not scheduling `svc-rtc`. A flag honoured in
  only some stages is a half-disabled Module, which is worse than either state.
- **An App declares its stage.** An App belongs to one Module and targets one or more
  pipeline stages; the manifest carries both, and the stage determines which container
  loads it.
- **Splitting a stage per Module may mean splitting several.** Giving Bot its own action
  container does not isolate Bot — its ingest and process code still shares. Isolating a
  Module properly means splitting every stage it touches, which is why the escape hatch is
  reserved for evidence rather than anticipation.

Four more containers, each for a specific reason rather than by default:

| Container | Why it is not in the pipeline |
|-----------|-------------------------------|
| `hub-webui` | static SPA assets; different cache and scaling profile entirely |
| `hub-api` | admin + marketplace + tenant management; low-volume admin traffic |
| `svc-core` | identity, security, credentials, entitlement — every stage depends on it, so it must not redeploy on an admin-UI change |
| `svc-rtc` | WebRTC/SFU media; UDP transport and media scaling share nothing with HTTP request handling |

Seven, from ~40.

`svc-core` is deliberately not folded into `hub-api`: doing so would put every service's
auth path on the admin API's deploy cadence, so a webui change could take down
authentication. `svc-rtc` cannot co-locate at all — media transport constrains and is
constrained by anything sharing its pod.

The router split is a **code and dependency-direction** split, not a deployment one. Both
halves ship in `svc-process`; "Modules never import each other" is enforced at package
level, where it is actually checkable, not by pod boundaries.

### What Module toggling means now

This is the honest trade-off of consolidation, and it is a real change from a
pod-per-Module design:

```yaml
modules:
  bot:       { enabled: true }
  social:    { enabled: true }
  customer:  { enabled: false }   # its Apps are not loaded; no pod disappears
  marketing: { enabled: false }
```

Turning a Module off stops the containers from loading that Module's App bundles. It
does **not** remove a workload. Consequences to accept knowingly:

- A disabled Module costs approximately nothing at runtime if its packages are never
  imported, but the container is still shared.
- A crash in one Module's first-party App can take down the others sharing that pod. This
  is the price of seven containers instead of forty.

### When to split a container

Container count is a values decision, not an architectural fact. A pipeline stage can be
run per Module when a Module earns it:

```yaml
svcAction:
  replicaSets:
    - name: svc-action-bot     ; modules: [bot]
    - name: svc-action-social  ; modules: [social]
```

The pipeline stages are the natural split points because their scaling axes already
differ; splitting *within* a stage by Module is the exception that needs evidence.

Reach for this on evidence, not anticipation — a Module whose crashes are hurting others,
or whose scaling profile genuinely diverges. Starting split is how the ~40 happened.

Third-party Apps need none of this: they are always reached across a network boundary
(`webhook_push` or `rest_pull` — see Apps), so vendor code never shares a process with ours
regardless of topology.

## Documentation

`docs/` is 435 files and 615,000 words across 60 directories, **43 of which are one-per-module**
and dissolve entirely in v3. 277 files reference the old module and path names.

The staleness has already started and nothing catches it: of 61 repository paths referenced
in docs, **26 no longer exist** — a whole family of `*_interaction_module_flask/` directories
among them. There is no docs check in CI of any kind.

That is the failure mode to design against. Docs do not go stale because nobody cares; they
go stale because nothing fails when they do.

### Docs are a per-phase gate, not a final phase

The obvious plan — migrate the code, then fix the docs at P5 — is what produces a 615k-word
corpus describing a system that no longer exists. Instead, **every phase's exit gate includes
its own documentation**, and a phase is not done until its docs are.

### A docs check that can actually fail

A gate nobody can fail is not a gate. CI grows a reference validator:

- extract every repository path referenced in `docs/**/*.md`
- assert each exists
- fail on any that does not

Seed it at the current baseline of **26 dead references** and ratchet the allowed count down,
never up. That makes the existing debt visible without blocking P0 on it, and makes any *new*
dead reference an immediate failure. Report the count of paths examined alongside the count
of failures — a validator that finds zero references is broken, not clean.

### Structure follows the hierarchy

The 43 per-module directories are replaced by the layering this design introduces:

```
docs/
  core/           one page per Core service
  modules/        social · customer · bot · marketing
    <module>/features/    one page per Feature contract, versioned with it
  apps/           first-party App manifests and how to write a third-party one
  deployment/     the seven containers, streams, tenancy, SPIFFE
```

A Feature's documentation is versioned with its contract. That is the page a third-party App
author reads, so letting it drift is a public-API problem, not an internal tidiness one.

### Delete, do not migrate

Much of 615k words describes modules that will not exist in the same shape. Carrying it
forward unexamined is worse than deleting it — a wrong page costs more than a missing one,
because it is trusted. Each phase's docs work explicitly includes deletions, and the count of
pages deleted is reported alongside pages written.

`README.md` and `docs/index.md` are rewritten last, at P5, once the structure beneath them is
true.

## Decisions

### Resolved

**`services/` is deleted — in two parts, at two different times.** Analysis of every
`services/*/Dockerfile` shows the tree is two unrelated things:

| Part | State | When |
|------|-------|------|
| 21 `*_module/` subdirectories | **provably dead** — each shadowed at build time by a `COPY` from the canonical tree | deleted in P0 |
| 11 aggregator `app.py` / `config.py` / `requirements.txt` | **live**, and the prototype for the seven containers | harvested in P0, removed at P5 |

Deleting only once we have confirmed nothing needs it — the standing condition — is satisfied
for the 21 by proof rather than by waiting: nothing builds from them, so removing them cannot
affect parity. The aggregators genuinely do need parity confirmed first, so they go at P5.

`docs/MODULE_CANONICAL_SOURCES.md` documents **3** orphans. The real number is **21**, which
is a reasonable measure of how quickly an undocumented duplicate tree drifts out of anyone's
model of the system. Diverged config is ported out of all 21 before deletion, not just the
three that were noticed.

`services/interactive-social/app.py` is 846 lines already merging four modules into one Quart
app. The seven-container consolidation is therefore partly prototyped rather than green-field
— harvest it, but replace its `sys.path.insert` imports with real packaging.

**`core/module_rtc` is rewritten in Rust** during P3, per the Go phase-out rule. It stays
`svc-rtc` either way — UDP media transport cannot share a pod with HTTP stages — so the
decision is language, not placement.

**Tier mapping** — see below. The starting mapping is derived; the residual split is
commercial.

### Tier mapping

Derived from `critical-rules.md`'s tier table and what v2.2.x already gates. Every row cites
its source; rows sourced from "this design" are proposals, not standards.

| Capability | Tier | Source |
|------------|------|--------|
| All four Modules, core functionality | Free | `critical-rules.md` — "Core product, no license-gated functionality" |
| Bot: platform connectors, commands, interactions | Free | ungated in v2.2.x |
| Social: chat, presence, communities | Free | ungated in v2.2.x |
| Customer: accounts, contacts, opportunities | Free | lightweight by v3.0.0 scope |
| Marketing: manual posting | Free | lightweight by v3.0.0 scope |
| More than one admin | Professional | `critical-rules.md` — Free is capped at 1 admin |
| **More than one tenant** | **Enterprise** | Free and Professional are both capped at the single default tenant; matches WaddleAI, where multi-tenancy is Enterprise |
| Whitelabelling | Professional | `critical-rules.md` |
| Google OAuth2 SSO | Professional | `critical-rules.md` |
| Analytics: `community_health`, `bad_actor_detection`, `user_journey`, `retention_cohorts`, `engagement_funnels` | Professional | v2.2.x `analytics_core_module` `PREMIUM_FEATURES` |
| Video proxy: 10 destinations, 5×2K, 15 Mbps, 90-day retention | Professional | v2.2.x `video_proxy_module` `PREMIUM_LIMITS` |
| Marketing: scheduling and cross-platform publishing | Professional | this design — the paid half of Marketing |
| SAML 2.0 / OIDC SSO | Enterprise | `critical-rules.md` |
| Audit logs, external KMS | Enterprise | `critical-rules.md` |
| WaddleAI integration | Enterprise | `critical-rules.md` |
| Advanced analytics | Enterprise | `critical-rules.md` |
| Dedicated Valkey / per-tenant infrastructure isolation | Enterprise | this design — see Transport limits |

### Two deployment topologies

Waddles ships in two shapes, and they differ in *who owns the deployment* — which changes
where entitlement attaches:

| | Self-hosted | SaaS (`waddles.app`) |
|---|---|---|
| Owner | the customer | PenguinTech |
| Tenants | 1 (Free/Pro) or many (Enterprise) | many — one per Enterprise customer, plus PenguinTech's default |
| Customer buys | a licence for their deployment | **a tenant**, or **an upgrade to their community inside our default tenant** |
| Entitlement attaches at | the tenant | the tenant *or* the community |

The second SaaS shape is the one that breaks an assumption elsewhere in this design.
Self-serve customers do not get a tenant at all — they get a **community inside PenguinTech's
default tenant**, and they pay to upgrade *that community*. Many paying customers at different
tiers therefore share one tenant.

#### Entitlement resolves narrowest-first, like App binding

Tier can no longer be a property of the tenant alone:

```
community entitlement  →  tenant entitlement
```

The same shape as App binding (`community → tenant → default`), and for the same reason: the
narrower scope is where the specific answer lives. In self-hosted deployments entitlement is
set at the tenant and communities inherit it; in SaaS shape two it is set per community and
overrides the default tenant's Free baseline.

This makes the structural caps clearer rather than murkier — they describe what a *customer*
gets, not what a deployment contains:

| Customer tier | Self-hosted | SaaS |
|---------------|-------------|------|
| Free | one deployment, the default tenant | a community in PenguinTech's default tenant |
| Professional | one deployment, the default tenant | a community in PenguinTech's default tenant |
| Enterprise | own deployment, many tenants | **their own tenant** |

PenguinTech's SaaS deployment holds many tenants because PenguinTech operates it, not because
it holds an Enterprise licence. Deployment size and customer tier are unrelated.

#### The domain is a mode switch, not a bypass

SaaS mode activates on **`waddles.app`** or **`waddles.penguincloud.tech`**. The hostname
therefore selects one of three modes, rather than toggling licensing on and off:

| Domain | Mode | Entitlement |
|--------|------|-------------|
| `waddles.app`, `waddles.penguincloud.tech` | **SaaS** | per tenant *or* per community, from billing — **never bypassed** |
| `*.penguintech.cloud`, `*.penguincloud.io` | internal (beta/dev) | bypassed — PenguinTech's own non-production |
| anything else | self-hosted | per-tenant licence validated against `license.penguintech.io` |

Reading the domain as a mode rather than a bypass is what keeps the SaaS chargeable. The two
questions collapse into one in self-hosted deployments and separate in SaaS:

| Question | Answered by | In SaaS |
|----------|-------------|---------|
| Is this *deployment* licensed to run? | the mode | yes — PenguinTech owns it |
| What tier is this *customer*? | the entitlement lookup | **never by the hostname** |

**A standards conflict to settle before launch.** `penguintech.md` lists product-specific
`.app` domains as hardcoded licence-bypass domains, and `waddles.app` is the product domain
per `penguintech-reference`. Applied literally, every paying SaaS customer would get full
entitlement free. Today's code happens to be correct — `PREMIUM_BYPASS_DOMAINS` in
`video_proxy_module` lists only `waddlebot.penguintech.io`, `waddles.penguintech.cloud` and
`waddles.penguincloud.io` — but that is luck rather than design. Raise the wording with the
standards owner; `waddles.penguincloud.tech` is also outside every current bypass pattern and
needs adding to the mode list explicitly.

#### Where community-scoped entitlement lives

The licence server has no sub-tenant entitlement scope — entitlement is licence-level. SaaS
shape two needs entitlement *below* the tenant, so it does not belong there:

| Entitlement | System | Covers |
|-------------|--------|--------|
| Deployment / tenant tier | licence server | self-hosted licences; Enterprise tenants in SaaS |
| **Community tier within a shared tenant** | **marketplace subscriptions** | SaaS self-serve customers |
| Third-party App access | marketplace subscriptions | both topologies |

The marketplace is already a billing system — `subscriptionController`, `premiumController`,
seat limits, overage pricing. Extending it to carry first-party Feature entitlement for a
community is a smaller change than adding a sub-tenant scope to the licence server for the
only two products that need it.

That does widen the marketplace's role: it currently gates third-party Apps, and in SaaS it
would also gate first-party Features for communities. State that deliberately rather than
letting it happen — it makes the marketplace load-bearing for revenue, not just for extensions.

### Structural caps

Two caps are structural rather than feature flags — they limit how many of a thing exists,
not what it can do:

| Cap | Free | Professional | Enterprise |
|-----|------|--------------|------------|
| Admins | 1 | many | many |
| **Tenants** | **1 (default)** | **1 (default)** | **many** |

Enforce tenant creation the way `critical-rules.md` enforces seats, not nodes: **block
creation of a second tenant with an upgrade path, and never touch the existing one.** Tenant
creation is a deliberate administrative act, so blocking it is safe; degrading an existing
tenant would not be.

**The residual commercial decision:** v2.2.x is effectively **two-tier** (free vs `premium`,
with 83 `premium` references and `PREMIUM_BYPASS_DOMAINS`). The standard mandates three. Every
capability currently marked `premium` therefore has to land in Professional *or* Enterprise,
and the rows above are a proposal for that split, not a reading of it. Confirm before P1
seeds `waddles.py`.

### A tier-name collision to settle

The license server's tier enum is `("community", "professional", "enterprise")` — see
`api/app/seeds/waddleai.py`. `critical-rules.md`'s table names the same tier **Free**.

For most products that inconsistency is cosmetic. For Waddles it is not: **community is a
first-class entity here** — the team/org level of `global → tenant → community`. A tier named
`community` and an entity named `community` in the same codebase will produce exactly the
kind of ambiguity the Vocabulary section exists to prevent.

Use `free` in `seeds/waddles.py` and raise the mismatch with the license-server team rather
than adopting `community` locally.

### Still open

**Which SPIRE root, per environment.** Independent (self-signed child) is the default and
needs no decision. Nesting under SkausWatch's root needs a join token minted there and its
trust bundle published to this cluster — cross-team coordination, not a code change. Blocks
nothing; alpha can run self-signed while beta nests.

## Migration phases## Migration phases

Detail lives in the companion plan. Summary:

| Phase | Work | Gate to exit |
|-------|------|--------------|
| P0 | Extract Core; delete `services/`'s 21 dead subdirs and harvest its aggregators; **propagate tenant scoping into the Python fleet**; Valkey + Streams as the stage transport; SPIFFE/SPIRE workload identity; collapse to seven containers; docs gate + restructure | Orphaned subdirs gone and every image still builds; cross-tenant isolation, redelivery, DLQ and idempotency tests all pass after first being made to fail; zero Alpine or unpinned images; gRPC call sites classified with counts |
| P1 | App manifest, registry, binding resolution; rename to `app_installations`; convert 2–3 Bot units as proof | A community can rebind a Feature to a non-default App |
| P2 | Bot — all triggers/actions/interactions become Apps | v2.2.x Bot parity, all as Apps |
| P3 | Social — community, presence, RTC, browser-source as Apps | v2.2.x Social parity |
| P4 | Customer + Marketing lightweight Apps | accounts/contacts/opportunities; scheduling + analytics |
| P5 | Cut v3.0.0 | parity verified against v2.2.x |

## Risks

| Risk | Mitigation |
|------|------------|
| Tenant scoping lands late, so Feature/App gating is built on an untrustworthy claim | It is P0, before any App conversion; nothing above it is sound until it passes |
| Feature contracts churn after third-party Apps exist | Version interfaces from P1; never ship an unversioned contract |
| The two trees (`action/` + `services/`) diverge further during migration | The 21 dead subdirs are deleted in P0, before any App conversion touches them; only the aggregators survive, and they are build inputs so drift is visible |
| "Lightweight CRM" expands under its own gravity | Customer's v3.0.0 scope is fixed at accounts/contacts/opportunities; anything more is 3.x |
| Per-community App execution becomes an untrusted-code surface | Not in-process — `webhook_push`/`rest_pull` keep vendors across a network boundary. P1 must instead carry per-App egress allowlisting and timeout policy |
| Seven shared containers widen blast radius vs. ~40 isolated ones | Accepted knowingly; pipeline stages are the split points when a Module earns one on evidence |
| Consolidation loses per-module health signal | Each App reports its own health through the stage's health endpoint, not one liveness probe per Module |
| Streams add an at-least-once duplicate-delivery failure mode the current synchronous calls do not have | Envelope ids and consumer-side dedupe are mandatory from P0, with a redelivery test that has been made to fail |
| Valkey becomes a single point of failure for the whole event path | It already is for cache and sessions; P0 sizes it for stream retention and configures persistence deliberately rather than inheriting cache defaults |
| Per-tenant streams and ACL users grow linearly with the tenant roster | Pool per tenant with idle eviction and an active-tenant set; revisit in the low thousands, then shard via Cluster hash tags or dedicated Valkey rather than dropping isolation |
| A "missing tenant means default" fallback outlives the migration and becomes a bypass | The fallback has a recorded cutoff date, after which unclaimed tokens are rejected |
| The multi-tenant path rots because Free and Professional never exercise it | Single-tenant runs the identical code with N=1; no `if tenant == "default"` shortcut is permitted anywhere |
| `waddles.app` is added to the bypass list per the standard, and the SaaS becomes free for every customer | The hostname selects a mode, never an entitlement; a test asserts a Free community on `waddles.app` resolves to Free |
| The marketplace becomes load-bearing for revenue but is sized as an extension catalogue | Stated deliberately in the design; its availability requirements are set for the billing path, not the browse path |
| SPIRE deployed standalone, then federation with SkausWatch needs a topology change | Deploy as `child` with the upstream disabled from the start; promotion is a values flip plus a join token |
| mTLS is treated as replacing the inter-service JWT | `security.md` requires both regardless of transport; the SVID-required test does not assert the JWT, so both need their own gate |
| mTLS is enabled without a peer SPIFFE ID allowlist, so any workload in the trust domain is accepted | Per-service accepted-peer lists, with a test asserting a valid-but-unlisted SVID is rejected |
| Middleware layers get reordered during refactoring, and the happy path still passes | The ordering contract has its own test that reverses the layers and confirms the reversal is caught |
| Docs are deferred to P5 and end up describing a system that no longer exists | Docs are a per-phase exit gate, backed by a reference validator that ratchets from a measured baseline of 26 dead references to zero |
| 615k words are migrated unexamined, so wrong pages outlive the modules they describe | Each phase reports pages deleted alongside pages written; a wrong page costs more than a missing one |
| CI rebuilds everything on any change | Seven images with path-filtered workflows, as `build-*.yml` already does per module |
