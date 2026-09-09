"""Social alias process bundle -- resolves and manages custom command aliases.

Ported from action/interactive/alias_interaction_module/services/alias_service.py.
Handles alias resolution (expands !<alias_name> to the stored command template with
variable substitution) and alias management commands (!alias add/list/delete).

Non-alias chatter returns None; alias commands return a response PlatformEvent.
Uses the frozen bundle runtime API for DAL and context access.
"""

from __future__ import annotations

import asyncio
import dataclasses
import re

from flask_core import PlatformEvent, get_bundle_context, get_bundle_dal

# Alias command patterns
_ALIAS_CMD_PATTERN = re.compile(r"^!alias\s+(\w+)(?:\s+(.+))?$", re.IGNORECASE)
_ALIAS_BARE_PATTERN = re.compile(r"^!alias\s*$", re.IGNORECASE)
_ALIAS_INVOKE_PATTERN = re.compile(r"^!(\w+)(?:\s+(.*))?$")

_ALIAS_USAGE = "Usage: !alias add <name> <command> | !alias list | !alias delete <name>"


async def transform(event: PlatformEvent) -> PlatformEvent | None:
    """Process alias commands and resolutions.

    Parses the incoming message. If it's an alias management command (!alias add/list/delete),
    handles it and returns a response. If it's an alias invocation (!<alias_name>), expands it
    with variable substitution and returns the expanded text. Otherwise returns None.

    Bare `!alias` (no subcommand at all) gets a usage-hint reply rather than
    being treated as an (always-missing) alias named "alias".

    Raises ValueError on a malformed event.
    """
    text = event.payload.get("text")
    if not isinstance(text, str) or not text or not text.strip():
        raise ValueError("event payload missing required 'text' string field")

    text = text.strip()

    if _ALIAS_BARE_PATTERN.match(text):
        return dataclasses.replace(event, payload={**event.payload, "text": _ALIAS_USAGE})

    # Check if it's an alias management command
    alias_cmd_match = _ALIAS_CMD_PATTERN.match(text)
    if alias_cmd_match:
        return await _handle_alias_command(event, alias_cmd_match)

    # Check if it's an alias invocation
    invoke_match = _ALIAS_INVOKE_PATTERN.match(text)
    if not invoke_match:
        return None  # Not an alias-related command

    alias_name = invoke_match.group(1)
    args_str = invoke_match.group(2) or ""

    # Try to expand the alias (returns None if not found)
    expanded = await _expand_alias(alias_name, event, args_str)
    if expanded is None:
        return None  # Not an alias, let other bundles handle it

    return dataclasses.replace(event, payload={**event.payload, "text": expanded})


async def _handle_alias_command(event: PlatformEvent, match: re.Match[str]) -> PlatformEvent | None:
    """Handle alias management commands (add/list/delete).

    Returns a response PlatformEvent with the command result.
    """
    subcommand = match.group(1).lower()
    args = match.group(2) or ""

    if subcommand == "add":
        response = await _cmd_add_alias(event, args)
    elif subcommand == "list":
        response = await _cmd_list_aliases(event)
    elif subcommand == "delete" or subcommand == "del":
        response = await _cmd_delete_alias(event, args)
    else:
        response = (
            f"Unknown alias command: {subcommand}. "
            "Use: !alias [add <name> <cmd>|list|delete <name>]"
        )

    return dataclasses.replace(event, payload={**event.payload, "text": response})


async def _cmd_add_alias(event: PlatformEvent, args: str) -> str:
    """Add a new alias. Args: <alias_name> <command_template>."""
    parts = args.split(maxsplit=1)
    if len(parts) != 2:
        return "Usage: !alias add <name> <command>"

    alias_name, command_template = parts
    if not _is_valid_alias_name(alias_name):
        return f"Invalid alias name: {alias_name}. Use alphanumeric characters and underscores."

    # Scope by community to prevent IDOR: aliases must not leak across
    # communities. Tenant-wide activations (ctx.community is None) cannot
    # add aliases -- there is no single community to own the alias.
    ctx = get_bundle_context()
    if ctx.community is None:
        return "Alias commands require a community context and cannot be used tenant-wide."

    try:
        dal = get_bundle_dal()
        community_id = int(ctx.community)

        # Use asyncio.to_thread since dal.insert_async may still need sync wrapper
        def _insert_alias() -> bool:
            dal.insert_async(
                dal.command_aliases,
                community_id=community_id,
                alias=alias_name,
                target_command=command_template,
                created_by=event.actor or "unknown",
            )
            return True

        await asyncio.to_thread(_insert_alias)
        return f"Alias '{alias_name}' created: {command_template}"
    except Exception as e:  # noqa: BLE001
        return f"Failed to create alias: {e}"


async def _cmd_list_aliases(event: PlatformEvent) -> str:
    """List all aliases for the community."""
    # Scope by community to prevent IDOR: never list another community's
    # aliases. Tenant-wide activations (ctx.community is None) have no
    # single community's aliases to list.
    ctx = get_bundle_context()
    if ctx.community is None:
        return "Alias commands require a community context and cannot be used tenant-wide."

    try:
        dal = get_bundle_dal()
        community_id = int(ctx.community)

        def _list_aliases() -> list[dict[str, object]]:
            query = (dal.command_aliases.community_id == community_id) & (
                dal.command_aliases.deleted_at.is_null()
            )
            rows = dal.select(query)
            return [dict(row) for row in rows]

        aliases = await asyncio.to_thread(_list_aliases)

        if not aliases:
            return "No aliases defined."

        lines = ["**Aliases:**"]
        for alias in aliases:
            lines.append(f"  - !{alias['alias']}: {alias['target_command']}")
        return "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return f"Failed to list aliases: {e}"


async def _cmd_delete_alias(event: PlatformEvent, args: str) -> str:
    """Delete an alias. Args: <alias_name>."""
    alias_name = args.strip()
    if not alias_name:
        return "Usage: !alias delete <name>"

    # Scope by community to prevent IDOR: never delete another community's
    # alias. Tenant-wide activations (ctx.community is None) have no single
    # community's aliases to delete.
    ctx = get_bundle_context()
    if ctx.community is None:
        return "Alias commands require a community context and cannot be used tenant-wide."

    try:
        dal = get_bundle_dal()
        community_id = int(ctx.community)

        def _delete_alias() -> bool:
            query = (dal.command_aliases.community_id == community_id) & (
                dal.command_aliases.alias == alias_name
            )
            rows = dal.select(query)
            if not rows:
                return False
            alias_id = rows.first().id
            dal.update(dal.command_aliases.id == alias_id, deleted_at=None)
            return True

        success = await asyncio.to_thread(_delete_alias)
        if success:
            return f"Alias '{alias_name}' deleted."
        return f"Alias '{alias_name}' not found."
    except Exception as e:  # noqa: BLE001
        return f"Failed to delete alias: {e}"


async def _expand_alias(alias_name: str, event: PlatformEvent, args_str: str) -> str | None:
    """Look up an alias and expand it with variable substitution.

    Returns None if the alias is not found, on error, or if there is no
    community context to scope the lookup to (tenant-wide activation) --
    the last case is silent (no error reply) so a typed word never leaks
    another community's alias or triggers a spammy failure reply.
    """
    try:
        ctx = get_bundle_context()
        if ctx.community is None:
            return None  # No community context -- do not expand across communities

        dal = get_bundle_dal()
        community_id = int(ctx.community)

        def _lookup_and_expand() -> str | None:
            query = (
                (dal.command_aliases.community_id == community_id)
                & (dal.command_aliases.alias == alias_name)
                & (dal.command_aliases.deleted_at.is_null())
            )
            rows = dal.select(query)

            if not rows:
                return None

            alias_row = rows.first()
            command_template: str = alias_row.target_command
            args = args_str.split() if args_str else []

            # Variable substitution (from v2 alias_service)
            substitutions = {
                "{user}": event.actor or "unknown",
                "{args}": " ".join(args) if args else "",
                "{arg1}": args[0] if len(args) > 0 else "",
                "{arg2}": args[1] if len(args) > 1 else "",
                "{all_args}": " ".join(args) if args else "",
            }

            expanded = command_template
            for var, value in substitutions.items():
                expanded = expanded.replace(var, value)

            # Update usage count (from v2 alias_service)
            dal.update(
                dal.command_aliases.id == alias_row.id,
                usage_count=(alias_row.usage_count or 0) + 1,
            )

            return expanded

        return await asyncio.to_thread(_lookup_and_expand)
    except Exception:  # noqa: BLE001
        return None  # Alias not found or error -- let other bundles handle it


def _is_valid_alias_name(name: str) -> bool:
    """Check if alias name is valid (alphanumeric + underscore, 1-30 chars)."""
    return bool(re.match(r"^[a-zA-Z0-9_]{1,30}$", name))
