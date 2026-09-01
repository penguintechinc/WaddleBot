"""Command registration -- port of `commandRegistrationService.js`.

Registers/unregisters a marketplace module's `trigger_commands` into the
shared `commands` table so the router module can dispatch them.

Node also broadcasts a `command:reload` Redis pub/sub event after every
register/unregister so already-running router instances pick up the
change without a restart. `hub_api`'s `HubAPIConfig` has no Redis wiring
yet (same gap already documented in `services/passkey_service.py` for a
different feature) and `redis` is not an installed dependency here
(`requirements.in`'s "not yet needed" comment lists it) -- reload
broadcast is therefore a documented gap, not silently dropped: command
rows are still correctly written/removed, only the live-reload signal is
missing until Redis is wired into this service (tracked the same way as
the `passkey_service.py` gap, not chased further in this port PR).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_MODULE_URL_BASE = "http://marketplace:8100/api/v1/internal/execute"


def register_module_commands(dal: Any, community_id: int, module: Any) -> None:
    """Insert/update every `module.trigger_commands` row for `community_id`.

    `module` is a `marketplace_modules` Row (or any object exposing `.id`,
    `.trigger_commands`, `.name`, `.description`, `.category`).
    """
    trigger_commands = module.trigger_commands or []
    if not trigger_commands:
        return

    module_name = f"marketplace:{module.id}"
    module_url = f"{_MODULE_URL_BASE}/{module.id}"
    category = module.category or "marketplace"
    now = datetime.now(UTC)

    for command in trigger_commands:
        description = module.description or command
        existing = (
            dal((dal.commands.command == command) & (dal.commands.community_id == community_id))
            .select()
            .first()
        )
        if existing is not None:
            dal(dal.commands.id == existing.id).update(
                module_name=module_name,
                module_url=module_url,
                is_enabled=True,
                updated_at=now,
            )
        else:
            dal.commands.insert(
                command=command,
                module_name=module_name,
                module_url=module_url,
                description=description,
                usage=command,
                category=category,
                permission_level="everyone",
                is_enabled=True,
                cooldown_seconds=3,
                community_id=community_id,
                created_at=now,
                updated_at=now,
            )
    dal.commit()


def unregister_module_commands(dal: Any, community_id: int, module_id: int) -> None:
    """Remove every command row registered for `module_id` in `community_id`."""
    module_name = f"marketplace:{module_id}"
    dal(
        (dal.commands.community_id == community_id) & (dal.commands.module_name == module_name)
    ).delete()
    dal.commit()


def get_community_commands(dal: Any, community_id: int) -> list[dict[str, Any]]:
    """Port of `routerIntegrationController.js::getCommunityCommands` -- `is_enabled` only."""
    rows = dal(
        (dal.commands.community_id == community_id)
        & (dal.commands.module_name.like("marketplace:%"))
        & (dal.commands.is_enabled == True)  # noqa: E712 -- pydal boolean idiom
    ).select()
    return [
        {
            "command": r.command,
            "moduleName": r.module_name,
            "moduleUrl": r.module_url,
            "description": r.description,
            "usage": r.usage,
            "category": r.category,
            "permissionLevel": r.permission_level,
            "isEnabled": bool(r.is_enabled),
            "cooldownSeconds": r.cooldown_seconds,
        }
        for r in rows
    ]


def get_registered_commands(dal: Any, community_id: int) -> list[dict[str, Any]]:
    """All marketplace-registered commands for `community_id`."""
    rows = dal(
        (dal.commands.community_id == community_id)
        & (dal.commands.module_name.like("marketplace:%"))
    ).select()
    return [
        {
            "command": r.command,
            "moduleName": r.module_name,
            "moduleUrl": r.module_url,
            "description": r.description,
            "usage": r.usage,
            "category": r.category,
            "permissionLevel": r.permission_level,
            "isEnabled": bool(r.is_enabled),
            "cooldownSeconds": r.cooldown_seconds,
        }
        for r in rows
    ]
