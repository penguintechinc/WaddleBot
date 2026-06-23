# Canonical Module Sources (Consolidated Services)

Several interaction modules exist in two locations. This documents which copy is
the **live build source** to prevent accidental edits to the wrong (orphaned) copy.

## interactive-social consolidated service

The `interactive-social` container is built from `services/interactive-social/Dockerfile`,
which COPYs the module code FROM `action/interactive/`:

```dockerfile
COPY action/interactive/alias_interaction_module    ./alias_interaction_module
COPY action/interactive/shoutout_interaction_module ./shoutout_interaction_module
COPY action/interactive/presence_module             ./presence_module
COPY action/interactive/quote_interaction_module    ./quote_interaction_module
```

`services/interactive-social/app.py` imports from these copied paths at runtime.

### Canonical vs orphaned

| Module | CANONICAL (built & run) | ORPHANED duplicate (wired into nothing) |
|--------|-------------------------|------------------------------------------|
| alias_interaction_module    | `action/interactive/alias_interaction_module/`    | `services/interactive-social/alias_interaction_module/` |
| shoutout_interaction_module | `action/interactive/shoutout_interaction_module/` | `services/interactive-social/shoutout_interaction_module/` |
| presence_module             | `action/interactive/presence_module/`             | `services/interactive-social/presence_module/` |

**Always edit the `action/interactive/` copies.** The `services/interactive-social/<module>/`
subdirectories are orphaned duplicates that have diverged (they carry a newer
component-based DB/Redis config) but are not referenced by the Dockerfile or app.py.
They are retained for now (not deleted) pending a decision on whether to port their
config improvements back into the canonical `action/` copies.
