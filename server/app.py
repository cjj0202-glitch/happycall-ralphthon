from pathlib import Path
from connexion import AsyncApp
from starlette.middleware.cors import CORSMiddleware


def create_app():
    api = AsyncApp(__name__, specification_dir=str(Path(__file__).parent))
    api.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
    # The launcher binds loopback. These are the only browser origins allowed to write.
    return CORSMiddleware(api, allow_origins=["http://localhost:3100", "http://127.0.0.1:3100"],
                          allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
                          allow_headers=["Content-Type", "X-Demo-Role"])


app = create_app()
