from dataclasses import dataclass

# Dataclass for discord payload, containing a channel_id and a server_id
@dataclass
class DiscordPayload:
    channel_id: str
    server_id: str