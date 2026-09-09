# Bot Command Argument Parsing (repo-local rule)

**All bot / App Bundle chat commands MUST parse arguments as nix-style CLI options/flags via the shared command parser — never ad-hoc, per-command string splitting.**

- Short flags `-x <value>`, positional trailing args, quoted strings respected.
- Each command declares its options declaratively (short flag, type, required, default, help). The framework parses BEFORE invoking the handler and emits a usage/error reply on bad input.
- Usage/help is generated from the declared options (`!help`, `!command --help`) — never hand-maintained.

**Examples of the required style:**
- `!poll -t <title> -T <ttl / time-to-expire> <poll options...>`
- `!timer -m <minutes> -l <lines of chat required or skipped> <message>`

**Applies to:** every command in `bot_process` (the router) and every feature/App-Bundle command, first-party and third-party.

**Implementation + tracking:** the shared parser is tracked in GitHub issue #301; a command's option schema is part of its bundle manifest (issue #293, alongside the config schema). New and ported command bundles use the shared parser, not bespoke parsing — migrate existing ad-hoc parsers (`!quote`/`!poll`/`!alias`/`!forum`) as they're touched.
