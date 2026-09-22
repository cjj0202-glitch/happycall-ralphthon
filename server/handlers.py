"""Thin OpenAPI handlers. Business state changes live in CaseService."""
from connexion import request
from starlette.concurrency import run_in_threadpool

from server.errors import DemoError
from server.runtime_storage import get_runtime_storage, storage_unavailable


def service():
    runtime = get_runtime_storage()
    if runtime.backend in ("vercel-blob", "dynamodb"):
        runtime.check_ready()
    return runtime.service


def error(exc):
    return {"error": {"code": exc.code, "message": exc.message}}, exc.status


async def health():
    from server.runtime_config import require_demo_api_key
    try:
        require_demo_api_key()
        ready = True
    except DemoError:
        ready = False
    # liveReady covers key/policy only, not model-provider authentication.
    try:
        budget_status = await run_in_threadpool(lambda: get_runtime_storage().check_ready())
    except Exception:
        return error(storage_unavailable())
    return {"status": "ok", "synthetic": True, "runtime": "synthetic-demo", "liveReady": ready, "budget": budget_status}


async def list_cases():
    try:
        return await run_in_threadpool(lambda: service().list())
    except DemoError as exc:
        return error(exc)


async def get_case(case_id):
    try:
        return await run_in_threadpool(lambda: service().get(case_id))
    except DemoError as exc:
        return error(exc)


async def create_intake(body, x_idempotency_key=None):
    try:
        # Connexion does not inject header parameters into the handler. Its local
        # request proxy is false outside an operation (e.g. direct adapter checks).
        request_key = request.headers.get("X-Idempotency-Key") if request else x_idempotency_key
        return await run_in_threadpool(lambda: service().intake(body, request_key)), 201
    except DemoError as exc:
        return error(exc)


async def get_intake_attempt(request_key):
    try:
        return await run_in_threadpool(lambda: service().intake_attempt(request_key))
    except DemoError as exc:
        return error(exc)


async def analyze_case(case_id, body):
    try:
        return await run_in_threadpool(lambda: service().analyze(case_id, body["mode"]))
    except DemoError as exc:
        return error(exc)


async def patch_case(case_id, body):
    try:
        role = request.headers.get("X-Demo-Role", "counselor")
        return await run_in_threadpool(lambda: service().patch(case_id, body, role))
    except DemoError as exc:
        return error(exc)


async def generate_reply_draft(case_id, body):
    try:
        role = request.headers.get("X-Demo-Role")
        return await run_in_threadpool(lambda: service().reply_draft(case_id, body, role))
    except DemoError as exc:
        return error(exc)
