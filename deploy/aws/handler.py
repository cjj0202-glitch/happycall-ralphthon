"""Lambda Python 3.12 / x86_64 entry point: handler.handler.

Function URL payload v2.0, buffered responses, same-origin static files and API.
Shared access credentials and DynamoDB settings come only from Lambda settings.
"""
import os
from pathlib import Path

from mangum import Mangum

from server.deployment_app import create_deployment_app


_environment = dict(os.environ)
_environment["ONEFLOW_STATIC_DIR"] = str(Path(__file__).resolve().parent / "apps/web/out")
app = create_deployment_app(environ=_environment)
# No startup jobs or shutdown state are required. Binary media use Mangum's
# default base64 conversion; adding audio/video to text_mime_types corrupts them.
handler = Mangum(app, lifespan="off")
del _environment
