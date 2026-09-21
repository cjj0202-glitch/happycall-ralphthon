"""Copied to api/index.py inside the self-contained deployment directory."""
import os
from pathlib import Path

from server.deployment_app import create_deployment_app


_bundle_root = Path(__file__).resolve().parents[1]
_environment = dict(os.environ)
_environment["ONEFLOW_STATIC_DIR"] = str(_bundle_root / "apps/web/out")
app = create_deployment_app(environ=_environment)
del _environment
