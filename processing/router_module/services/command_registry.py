"""Command Registry - Dynamic command registration and routing"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CommandInfo:
    """Command registration information"""
    command: str
    module_name: str
    module_url: str
    description: str
    usage: str
    category: str
    permission_level: str  # 'everyone', 'member', 'moderator', 'admin', 'owner'
    is_enabled: bool
    cooldown_seconds: int
    community_id: Optional[int] = None  # None = global command


class CommandRegistry:
    """Manages command registration and routing"""

    def __init__(self, dal, cache_manager):
        self.dal = dal
        self.cache = cache_manager
        self._command_cache: Dict[str, Dict[str, CommandInfo]] = {}  # {community_id: {command: info}}
        self._global_commands: Dict[str, CommandInfo] = {}

    async def initialize(self):
        """Initialize and load commands from database"""
        logger.info("Initializing command registry")
        await self._load_commands()
        logger.info("Command registry initialized")

    async def _load_commands(self):
        """Load all registered commands from database"""
        try:
            # For marketplace: prefixed commands, join marketplace_modules to verify module is active
            # module_name format: 'marketplace:{moduleId}'
            # This ensures we don't load commands from suspended or deleted marketplace modules
            result = self.dal.executesql(
                """SELECT c.command, c.module_name, m.url as module_url,
                          c.description, c.usage, c.category, c.permission_level,
                          c.is_enabled, c.cooldown_seconds, c.community_id
                   FROM commands c
                   LEFT JOIN hub_modules m ON m.name = c.module_name
                   LEFT JOIN marketplace_modules mm ON (
                       c.module_name LIKE 'marketplace:%' AND
                       mm.id = CAST(SPLIT_PART(c.module_name, ':', 2) AS INTEGER) AND
                       mm.deleted_at IS NULL
                   )
                   WHERE c.is_active = true
                   AND (
                       c.module_name NOT LIKE 'marketplace:%' OR
                       (mm.status = 'approved' AND mm.id IS NOT NULL)
                   )""",
                []
            )

            # Parse results
            for row in result:
                cmd_info = CommandInfo(
                    command=row[0],
                    module_name=row[1],
                    module_url=row[2] or f"http://{row[1]}:8000",  # Default port
                    description=row[3] or "",
                    usage=row[4] or "",
                    category=row[5] or "general",
                    permission_level=row[6] or "everyone",
                    is_enabled=row[7] if row[7] is not None else True,
                    cooldown_seconds=row[8] or 0,
                    community_id=row[9]
                )

                if cmd_info.community_id is None:
                    # Global command
                    self._global_commands[cmd_info.command] = cmd_info
                else:
                    # Community-specific command
                    if cmd_info.community_id not in self._command_cache:
                        self._command_cache[cmd_info.community_id] = {}
                    self._command_cache[cmd_info.community_id][cmd_info.command] = cmd_info

            logger.info(f"Loaded {len(self._global_commands)} global commands")
            logger.info(f"Loaded commands for {len(self._command_cache)} communities")

        except Exception as e:
            logger.error(f"Failed to load commands: {e}")

    async def get_command(self, command: str, community_id: Optional[int] = None) -> Optional[CommandInfo]:
        """Get command info by name and community"""
        # Check community-specific commands first
        if community_id and community_id in self._command_cache:
            if command in self._command_cache[community_id]:
                return self._command_cache[community_id][command]

        # Fall back to global commands
        if command in self._global_commands:
            return self._global_commands[command]

        return None

    async def list_commands(
        self,
        community_id: Optional[int] = None,
        category: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List available commands"""
        commands = []

        # Add community-specific commands
        if community_id and community_id in self._command_cache:
            for cmd_info in self._command_cache[community_id].values():
                if enabled_only and not cmd_info.is_enabled:
                    continue
                if category and cmd_info.category != category:
                    continue
                commands.append(asdict(cmd_info))

        # Add global commands
        for cmd_info in self._global_commands.values():
            if enabled_only and not cmd_info.is_enabled:
                continue
            if category and cmd_info.category != category:
                continue
            # Don't duplicate if already in community commands
            if not any(c['command'] == cmd_info.command for c in commands):
                commands.append(asdict(cmd_info))

        return sorted(commands, key=lambda x: x['command'])

    async def register_command(
        self,
        command: str,
        module_name: str,
        module_url: str,
        description: str = "",
        usage: str = "",
        category: str = "general",
        permission_level: str = "everyone",
        cooldown_seconds: int = 0,
        community_id: Optional[int] = None
    ) -> bool:
        """Register a new command"""
        try:
            # Check if command already exists
            existing = await self.get_command(command, community_id)
            if existing:
                logger.warning(f"Command {command} already registered, updating")
                return await self.update_command(
                    command, module_name, module_url, description,
                    usage, category, permission_level, cooldown_seconds, community_id
                )

            # Insert into database
            self.dal.executesql(
                """INSERT INTO commands
                   (command, module_name, description, usage, category,
                    permission_level, cooldown_seconds, community_id, is_enabled, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, true)""",
                [command, module_name, description, usage, category,
                 permission_level, cooldown_seconds, community_id]
            )

            # Add to cache
            cmd_info = CommandInfo(
                command=command,
                module_name=module_name,
                module_url=module_url,
                description=description,
                usage=usage,
                category=category,
                permission_level=permission_level,
                is_enabled=True,
                cooldown_seconds=cooldown_seconds,
                community_id=community_id
            )

            if community_id is None:
                self._global_commands[command] = cmd_info
            else:
                if community_id not in self._command_cache:
                    self._command_cache[community_id] = {}
                self._command_cache[community_id][command] = cmd_info

            logger.info(f"Registered command: {command} -> {module_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to register command {command}: {e}")
            return False

    async def update_command(
        self,
        command: str,
        module_name: str,
        module_url: str,
        description: str = "",
        usage: str = "",
        category: str = "general",
        permission_level: str = "everyone",
        cooldown_seconds: int = 0,
        community_id: Optional[int] = None
    ) -> bool:
        """Update existing command"""
        try:
            self.dal.executesql(
                """UPDATE commands
                   SET module_name = %s, description = %s, usage = %s,
                       category = %s, permission_level = %s, cooldown_seconds = %s
                   WHERE command = %s AND (community_id = %s OR (community_id IS NULL AND %s IS NULL))""",
                [module_name, description, usage, category, permission_level,
                 cooldown_seconds, command, community_id, community_id]
            )

            # Update cache
            cmd_info = CommandInfo(
                command=command,
                module_name=module_name,
                module_url=module_url,
                description=description,
                usage=usage,
                category=category,
                permission_level=permission_level,
                is_enabled=True,
                cooldown_seconds=cooldown_seconds,
                community_id=community_id
            )

            if community_id is None:
                self._global_commands[command] = cmd_info
            else:
                if community_id not in self._command_cache:
                    self._command_cache[community_id] = {}
                self._command_cache[community_id][command] = cmd_info

            logger.info(f"Updated command: {command}")
            return True

        except Exception as e:
            logger.error(f"Failed to update command {command}: {e}")
            return False

    async def unregister_command(self, command: str, community_id: Optional[int] = None) -> bool:
        """Unregister (soft delete) a command"""
        try:
            self.dal.executesql(
                """UPDATE commands SET is_active = false
                   WHERE command = %s AND (community_id = %s OR (community_id IS NULL AND %s IS NULL))""",
                [command, community_id, community_id]
            )

            # Remove from cache
            if community_id is None:
                self._global_commands.pop(command, None)
            elif community_id in self._command_cache:
                self._command_cache[community_id].pop(command, None)

            logger.info(f"Unregistered command: {command}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister command {command}: {e}")
            return False

    async def enable_command(self, command: str, community_id: Optional[int] = None) -> bool:
        """Enable a command"""
        return await self._set_command_enabled(command, community_id, True)

    async def disable_command(self, command: str, community_id: Optional[int] = None) -> bool:
        """Disable a command"""
        return await self._set_command_enabled(command, community_id, False)

    async def _set_command_enabled(
        self,
        command: str,
        community_id: Optional[int],
        enabled: bool
    ) -> bool:
        """Set command enabled/disabled state"""
        try:
            self.dal.executesql(
                """UPDATE commands SET is_enabled = %s
                   WHERE command = %s AND (community_id = %s OR (community_id IS NULL AND %s IS NULL))""",
                [enabled, command, community_id, community_id]
            )

            # Update cache
            if community_id is None and command in self._global_commands:
                self._global_commands[command].is_enabled = enabled
            elif community_id in self._command_cache and command in self._command_cache[community_id]:
                self._command_cache[community_id][command].is_enabled = enabled

            logger.info(f"{'Enabled' if enabled else 'Disabled'} command: {command}")
            return True

        except Exception as e:
            logger.error(f"Failed to set command enabled state: {e}")
            return False

    async def reload_commands(self):
        """Reload all commands from database"""
        logger.info("Reloading command registry")
        self._command_cache.clear()
        self._global_commands.clear()
        await self._load_commands()
