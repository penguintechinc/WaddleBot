# waddle_transports

Shared inbound/outbound transport-primitives library for Waddles
pipeline-stage services (`core/svc_action`, `core/svc_ingest`, and any
platform-specific connector bundle). Six transports, each declaring which
direction(s) it actually implements:

| Transport | sub_types | Outbound | Inbound |
|---|---|---|---|
| `http` | `webhook`, `rest_api`, `grpc`, `graphql` | all four | `rest_pull` (real); `webhook_push` is server-side, out of scope for a `receive()` client |
| `message_queue` | `valkey`, `aws_sqs`\*, `kafka`\* | `valkey` real | `valkey` real |
| `irc` | (none) | real | real |
| `socket` | (none) | real (generic) | real (generic) |
| `overlay` | `full_screen`, `media`, `crawler` | real | n/a (push-only) |
| `email` | `smtp` | real | `imap`\* |

\* Explicitly deferred (not stubbed) -- routed to a clean slot that raises
a documented "not yet implemented" error rather than silently pretending
to work. See each transport module's own docstring for the reason and
what a follow-up implementation needs.

`transports/irc_relay.py`'s `RelayOutboundIrcTransport` is a **separate,
topology-specific** outbound-only variant of `irc` -- for a caller whose
real IRC socket is held by a *different process* (e.g. svc-ingest's
`TwitchIrcReceiver`), it relays a send through a Valkey queue instead of
opening a second connection. Not wired into `get_transport()` (import it
directly) -- see that module's own docstring.

## Usage

```python
from waddle_transports.registry import get_transport
from waddle_transports.types import TransportType

transport = get_transport(TransportType.HTTP, http_client=my_httpx_client)
result = await transport.send(
    config={"sub_type": "webhook", "url": "https://...", "secret_ref": "MY_SECRET"},
    payload={"text": "hello"},
)
```

## Design

- `types.py` -- `TransportType`/`Direction` enums.
- `base.py` -- `Transport` ABC (`send()`/`receive()`), `TransportResult`,
  `RetryableTransportError`/`NonRetryableTransportError`.
- `registry.py` -- `get_transport(transport_type, ...) -> Transport`.
- `transports/` -- one module per transport, each exporting a
  `Transport` subclass.

Consumers pass plain `Mapping[str, Any]` config/payload dicts, not an
app-specific dataclass -- this library has no dependency on any one
service's own envelope/target model, by design (both `svc-action`'s
outbound dispatch and `svc-ingest`'s inbound poll/consume import the same
package).
