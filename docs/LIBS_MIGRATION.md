# Shared libs/ — Canonical Source & Fork Status

## Canonical location: root `/libs/`

The root `/libs/` directory is the canonical shared-library source. It is COPYed
into ~39 service Docker images (e.g. `COPY libs/flask_core /app/libs/flask_core`)
and imported by modules across `action/`, `core/`, `trigger/`, `services/`, and `sdk/`.

Subdirectories: `flask_core/`, `platform_receiver/`, `calendar_sync/`, `module_sdk/`,
`presence/`, `grpc_protos/`.

## Known fork: `services/core-community/libs/flask_core/`

`services/core-community/libs/flask_core/` is a **diverged fork** of the root copy:
- Root `/libs/flask_core/` uses **PyDAL** for database operations.
- The core-community fork uses **penguin-dal** (the standards-mandated runtime DAL).
- Divergence is concentrated in `database.py` and `read_replica.py` (DATABASE_URL
  construction and read-replica logic).

All other libs subdirectories (`platform_receiver`, `calendar_sync`, `module_sdk`,
`presence`, `grpc_protos`) are byte-identical between the two locations.

## Intended end state

Per project standards, **penguin-dal is mandatory for all runtime DB operations**.
The correct long-term fix is to reconcile root `/libs/flask_core/` onto penguin-dal
(matching the core-community fork) and remove the duplicate, OR migrate all modules
to the published `penguin-dal` / `penguin-libs` packages and delete the vendored
`libs/` copies entirely.

This is a dedicated migration, tracked separately — NOT a cleanup deletion, because
deleting either copy today would break builds.
