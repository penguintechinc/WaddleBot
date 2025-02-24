from dataclasses import dataclass

@dataclass
class gateway():
    gateway_type: str
    gateway_server: str
    channel_id: str
    is_active: bool

@dataclass
class identityPayload():
    identity_name: str

@dataclass
class activity():
    name: str
    amount: int

@dataclass
class contextPayload():
    userid: int
    activity: str
    amount: int
    text: str
    namespace: str
    namespaceid: int
    platform: str