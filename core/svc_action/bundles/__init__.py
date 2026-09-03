"""App Bundle action-stage scripts bundled with the svc-action image.

Real bundles are marketplace/first-party packages shipped with (or synced
into) each stage-runner's image, same convention `core/svc_process/
bundles/`/`core/svc_ingest/bundles/` establish for their own stages. This
package holds `discord_send_action.py` -- the first real (non-demo)
action-stage bundle, ported from `action/pushing/discord_action_module`'s
`send_message` to prove the App Bundle SDK's script-entrypoint model
extends to the action stage, not just ingest/process.
"""
