"""Video Proxy Module Services."""

from .database import init_database, get_db
from .stream_key_service import (
    generate_stream_key,
    validate_stream_key,
    regenerate_stream_key,
    get_stream_config,
)
from .destination_service import (
    add_destination,
    remove_destination,
    update_destination,
    list_destinations,
    set_force_cut,
    count_2k_destinations,
)
from .license_service import (
    is_premium,
    get_limits,
    can_add_destination,
    can_add_2k_destination,
)

__all__ = [
    "init_database",
    "get_db",
    "generate_stream_key",
    "validate_stream_key",
    "regenerate_stream_key",
    "get_stream_config",
    "add_destination",
    "remove_destination",
    "update_destination",
    "list_destinations",
    "set_force_cut",
    "count_2k_destinations",
    "is_premium",
    "get_limits",
    "can_add_destination",
    "can_add_2k_destination",
]
