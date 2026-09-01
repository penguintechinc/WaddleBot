# Changelog

- [v2.0.0](#v200)

> **Note:** the entries previously listed here for v1.38.1 down through v0.1.0 were not Waddles's
> own release history — they were the changelog of an unrelated third-party tool (`hbagdi/deck` /
> `Kong/deck`) that had been pasted into this file by mistake, and have been removed. For pre-v2.0
> history, see `git log` and this repo's [GitHub releases](https://github.com/penguintechinc/waddlebot/releases).
> v3.0.x work is tracked on `release/v3.0.X` and is not yet tagged as a numbered release — see
> [`ARCHITECTURE.md`](../ARCHITECTURE.md) for current build status.

## [v2.0.0]

> Release date: 2026/02

### ⚠️ Breaking Changes (v1.x → v2.0)

This is a major version release. The following v1.x APIs and patterns are removed or replaced without backward compatibility shims — the version bump signals this intentionally.

#### Marketplace & Vendor APIs

The hub module's internal marketplace and vendor routes (`/api/v1/hub/marketplace/*`, `/api/v1/hub/vendor/*`) are no longer the source of truth for module management. All marketplace, vendor, and premium business logic now lives exclusively in the **marketplace module**.

| Old route (hub module) | Replacement (marketplace module) |
|------------------------|----------------------------------|
| `GET /api/v1/hub/marketplace/modules` | `GET /api/v1/marketplace/catalog` |
| `POST /api/v1/hub/marketplace/install` | `POST /api/v1/marketplace/communities/:cid/install` |
| `GET /api/v1/hub/vendor/submissions` | `GET /api/v1/marketplace/vendor/modules` |
| `POST /api/v1/hub/vendor/submit` | `POST /api/v1/marketplace/vendor/modules/:id/submit` |
| `GET /api/v1/hub/marketplace/vendor-requests` | `GET /api/v1/marketplace/admin/marketplace/vendor-requests` |

#### Database

- `hub_module_installations` and `marketplace_subscriptions` remain for install tracking, but the **`marketplace_catalog` VIEW** is now the single source for browsing (merges `hub_modules` + `marketplace_modules`).
- New required columns on `marketplace_modules`: `communication_model`, `integration_type`, `auth_type`, `auth_config`, `api_base_url`, `tenant_id`, `seller_id` — run migration `059_marketplace_consolidation.sql`.
- New table: `community_premium_subscriptions`.

#### Vendor module communication

Vendor modules now declare a `communication_model` (`webhook_push` or `rest_pull`) and `integration_type` (`action`, `trigger`, `interaction`, `command_handler`). The router dispatches all marketplace module commands through the marketplace proxy at `/api/v1/marketplace/internal/execute/:moduleId` — vendor endpoints are never called directly by the router.

#### Frontend routes

| Old route | New route |
|-----------|-----------|
| `/admin/:communityId/marketplace` (list) | unchanged |
| _(none)_ | `/admin/:communityId/marketplace/:source/:id` (detail) |
| _(none)_ | `/admin/:communityId/premium` |
| _(none)_ | `/superadmin/marketplace-settings` |
