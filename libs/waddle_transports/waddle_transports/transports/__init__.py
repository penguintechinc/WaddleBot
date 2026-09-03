"""One module per transport -- `http`/`message_queue`/`irc`/`socket`/`overlay`/`email`.

Each exports one `waddle_transports.base.Transport` subclass. Resolve via
`waddle_transports.registry.get_transport(transport_type, ...)` rather
than importing a transport module directly, unless a caller specifically
wants to bypass the registry (e.g. a bundle script constructing its own
instance with custom wiring).
"""

from __future__ import annotations
