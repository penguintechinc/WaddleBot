"""Alias Service - Linux-style command alias management"""
from typing import Any, Dict, List, Optional


class AliasService:
    """
    Linux-style alias system for custom commands
    Supports variable substitution: {user}, {args}, {arg1}, {arg2}, {all_args}
    """
    def __init__(self, dal):
        self.dal = dal

    async def create_alias(self, community_id: str, alias_name: str, command: str, created_by: str) -> Dict[str, Any]:
        """Create new alias"""
        alias_id = await self.dal.insert_async(
            self.dal.aliases,
            community_id=community_id,
            alias_name=alias_name,
            command=command,
            created_by=created_by,
            usage_count=0
        )
        return {"id": alias_id, "alias_name": alias_name, "command": command}

    async def list_aliases(self, community_id: str) -> List[Dict[str, Any]]:
        """List all aliases for community"""
        query = (self.dal.aliases.community_id == community_id) & (self.dal.aliases.is_active is True)  # noqa: E712
        rows = await self.dal.select_async(query)
        return [dict(row) for row in rows]

    async def delete_alias(self, alias_id: str) -> bool:
        """Delete alias (soft delete)"""
        await self.dal.update_async(
            self.dal.aliases.id == alias_id,
            is_active=False
        )
        return True

    async def execute_alias(self, alias_name: str, user: str, args: List[str]) -> Optional[str]:
        """Execute alias with variable substitution"""
        # Get alias command
        query = (self.dal.aliases.alias_name == alias_name) & (self.dal.aliases.is_active is True)  # noqa: E712
        rows = await self.dal.select_async(query)

        if not rows:
            return None

        alias = rows.first()
        command = alias.command

        # Variable substitution
        substitutions = {
            '{user}': user,
            '{args}': ' '.join(args) if args else '',
            '{arg1}': args[0] if len(args) > 0 else '',
            '{arg2}': args[1] if len(args) > 1 else '',
            '{all_args}': ' '.join(args) if args else ''
        }

        for var, value in substitutions.items():
            command = command.replace(var, value)

        # Update usage count
        await self.dal.update_async(
            self.dal.aliases.id == alias.id,
            usage_count=alias.usage_count + 1
        )

        return command
