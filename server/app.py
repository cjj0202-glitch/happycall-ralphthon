from pathlib import Path
from connexion import AsyncApp
from starlette.middleware.cors import CORSMiddleware

from server.runtime_config import cors_origins


def create_app():
    allowed_origins = cors_origins()
    api = AsyncApp(__name__, specification_dir=str(Path(__file__).parent))
    api.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
    # This governs browser cross-origin access; it does not authenticate callers.
    return CORSMiddleware(api, allow_origins=allowed_origins, allow_credentials=False,
                          allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
                          allow_headers=["Content-Type", "X-Demo-Role"])


app = create_app()
