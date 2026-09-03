"""Persistent-socket receivers bundled with the svc-ingest image.

Each receiver holds one long-lived inbound connection (a Discord bot
gateway socket today, more platforms later), supervised via
`supervisor.ReceiverSupervisor` and lease-guarded via
`socket_lease.LeasedReceiver` so scaling svc-ingest never opens duplicate
sockets for the same `(provider, community)`.
"""
