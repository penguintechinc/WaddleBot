"""
Pytest bootstrap for svc-presentation's scaffold tests.

svc_presentation isn't installed as a package (it's a standalone
stage-runner directory run via `hypercorn app:app`, same shape as
core/browser_source_core_module) -- so, unlike libs/*_module's installable
packages, its own directory has to be put on sys.path explicitly for
`from app import app` / `import config` to resolve.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
