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
| event bus | **split from** `processing/router_module` | pub/sub spine all Modules emit to |
| workflow | `core/workflow_core_module` | cross-Module automation |
| analytics | `core/analytics_core_module` | shared telemetry sink |
| marketplace | `admin/marketplace_module` | catalog, vendors, subscriptions, App installs + bindings |
| hub | `admin/hub_module` | admin shell that mounts enabled Modules |
| entitlement client | new, wraps `penguin-licensing` + PostHog | the Feature gate |

### The router split

`processing/router_module` today mixes two concerns: generic event routing, and
Twitch/Discord command semantics (command registry, cooldowns, emote handling).

The generic half becomes the Core **event bus**. The command half stays in Bot. Without
this split, Social, Customer and Marketing would each have to depend on Bot to emit an
event — which would make the Modules interdependent and defeat global toggling.

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

## Open decisions

These need a call before the phases they block:

1. **`core/module_rtc` is Go.** It is the seed of Social's conferencing story — precisely
   where it would need to grow, which the Go phase-out rule says it should not. Rewrite in
   Rust during P3, or grant a documented exception. Blocks P3.
2. **The `services/` tree is a half-finished consolidation** with documented orphaned
   duplicates (`docs/MODULE_CANONICAL_SOURCES.md`). v3 either completes it or deletes it;
   keeping both trees is what produced the divergence. Blocks P0.
3. **Tier mapping is not yet set.** Which Features land in Free vs Professional vs
   Enterprise is a commercial decision, not an architectural one. Blocks the
   `seeds/waddles.py` definition in P1.

## Migration phases

Detail lives in the companion plan. Summary:

| Phase | Work | Gate to exit |
|-------|------|--------------|
| P0 | Extract Core; resolve the `services/` tree; **propagate tenant scoping into the Python fleet**; collapse to seven containers | Core deploys alone; one tree only; cross-tenant isolation test passes after first being made to fail |
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
| The two trees (`action/` + `services/`) diverge further during migration | Resolve in P0, before any App conversion touches them |
| "Lightweight CRM" expands under its own gravity | Customer's v3.0.0 scope is fixed at accounts/contacts/opportunities; anything more is 3.x |
| Per-community App execution becomes an untrusted-code surface | Not in-process — `webhook_push`/`rest_pull` keep vendors across a network boundary. P1 must instead carry per-App egress allowlisting and timeout policy |
| Seven shared containers widen blast radius vs. ~40 isolated ones | Accepted knowingly; pipeline stages are the split points when a Module earns one on evidence |
| Consolidation loses per-module health signal | Each App reports its own health through the stage's health endpoint, not one liveness probe per Module |
| CI rebuilds everything on any change | Seven images with path-filtered workflows, as `build-*.yml` already does per module |
