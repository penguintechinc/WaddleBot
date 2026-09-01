-- Migration 070: add a human-readable `name` column to app_catalog.
-- Follow-up to 069_app_bundle_tiers.sql -- that migration's app_catalog
-- table has no column for the bundle's display name (only `manifest_version`,
-- the bundle.yaml `version`), so a marketplace listing endpoint has nothing
-- to show a human besides the machine `app_id`
-- (`waddles.<module>.<feature>.<app>`). `libs/flask_core/flask_core/
-- app_manifest.py`'s `AppManifest.name` is required at manifest-parse time;
-- this column persists that same value so it survives a hub-api restart
-- (the in-memory AppRegistry does not).
--
-- Encryption at rest: engine-level (PostgreSQL volume/TDE per security.md
-- Encryption -- Storage baseline). No column-level action needed here.

ALTER TABLE app_catalog ADD COLUMN IF NOT EXISTS name TEXT;
