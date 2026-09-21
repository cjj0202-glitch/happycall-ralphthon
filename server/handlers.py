"""Thin OpenAPI handlers. Business state changes live in CaseService."""
from functools import lru_cache
from connexion import request
from starlette.concurrency import run_in_threadpool

from server.errors import DemoError
from server.repository import JsonCaseRepository
from server.service import CaseService
from server.budget import Budget


@lru_cache(maxsize=1)
def service():
    return CaseService(JsonCaseRepository())


def error(exc):
    return {"error": {"code": exc.code, "message": exc.message}}, exc.status


async def health():
    from scripts.demo_openai_env import read_env, REQUIRED_POLICY
    values = read_env()
    ready = bool(values.get("OPENAI_API_KEY")) and all(values.get(k) == v for k, v in REQUIRED_POLICY.items())
    return {"status": "ok", "synthetic": True, "runtime": "local-demo", "liveReady": ready, "budget": Budget().status()}


async def list_cases():
    try:
        return await run_in_threadpool(service().list)
    except DemoError as exc:
        return error(exc)


async def get_case(case_id):
    try:
        return await run_in_threadpool(service().get, case_id)
    except DemoError as exc:
        return error(exc)


async def create_intake(body):
    try:
        return await run_in_threadpool(service().intake, body), 201
    except DemoError as exc:
        return error(exc)


async def analyze_case(case_id, body):
    try:
        return await run_in_threadpool(service().analyze, case_id, body["mode"])
    except DemoError as exc:
        return error(exc)


async def patch_case(case_id, body):
    try:
        role = request.headers.get("X-Demo-Role", "counselor")
        return await run_in_threadpool(service().patch, case_id, body, role)
    except DemoError as exc:
        return error(exc)
