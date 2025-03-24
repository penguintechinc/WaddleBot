from dataclasses import dataclass


# Use the below for any database (web or direct) info being passed around
@dataclass
class dbinfo:
    host: str
    port: int
    user: str
    password: str
    database: str
    table: str


@dataclass
class identity:
    id: str
    reputation: float


@dataclass
class event:
    activity: str
    amount: float
    namespace: str
    platform: str
    interface: str
    subInterface: str
    rawText: str


@dataclass
class retvars:
    msg: str
    media: str
    stdout: str


@dataclass
class dbquery:
    columns: list
    table: str
    queryColumn: str
    queryValue: str
