"""Atomic intake retry/recovery contracts. No live providers or existing stores."""
import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock
import uuid
from unittest.mock import Mock, patch

import pytest

from server.cas_repository import CasCaseRepository
from server.cas_store import InMemoryCasStore
from server.errors import DemoError
from server.repository import JsonCaseRepository
from server.service import CaseService

ROOT = Path(__file__).resolve().parents[1]
BODY = {'storeId': 'SYN-TEST', 'subject': '합성 문의', 'text': '도착 확인 요청입니다.', 'type': 'missing'}


@pytest.fixture(params=['local', 'cas'])
def store(request, tmp_path):
    backing = InMemoryCasStore()
    def reopen():
        repo = (JsonCaseRepository(tmp_path / 'cases.json') if request.param == 'local'
                else CasCaseRepository(backing))
        analyzer = Mock()
        analyzer.analyze.side_effect = AssertionError('No live analysis in retry tests')
        return CaseService(repo, analyzer)
    return reopen


def error(code, status, operation):
    with pytest.raises(DemoError) as found:
        operation()
    assert (found.value.code, found.value.status) == (code, status)


def test_same_attempt_reopen_returns_one_case_and_current_revision(store):
    s = store()
    n = len(s.list()['cases'])
    key = str(uuid.uuid4())
    created = s.intake(BODY, key)
    retried = store().intake(dict(reversed(list(BODY.items()))), key.upper())
    assert retried == created
    assert len(store().list()['cases']) == n + 1
    assert len(created['history']) == 1
    updated = s.patch(created['id'], {'expectedRevision': 0, 'intake': {'request': '추가로 확인해 주세요.'}})
    assert store().intake(BODY, key) == updated
    assert store().intake_attempt(key) == updated
    assert 'intakeRequests' not in updated and key not in str(updated)
    assert len(store().list()['cases']) == n + 1


def test_different_input_reusing_key_is_conflict_without_write(store):
    s = store()
    key = str(uuid.uuid4())
    created = s.intake(BODY, key)
    original = s.list()
    for name, value in [('text', '다른 내용'), ('subject', '다른 문의'), ('storeId', 'OTHER'), ('type', 'wrong')]:
        error('IDEMPOTENCY_CONFLICT', 409, lambda: s.intake({**BODY, name: value}, key))
    assert store().list() == original
    assert store().intake_attempt(key) == created


def test_linked_intake_retry_survives_fixture_changes_without_bypassing_payload_binding(store):
    s = store()
    source = s.repo.fixtures()['cases'][0]
    body = {'storeId': source['intake']['storeId'], 'subject': source['intake']['subject'],
            'type': source['type'], 'text': '합성 연결 문의', 'referenceCaseId': source['id']}
    key = str(uuid.uuid4())
    created = s.intake(body, key)
    with patch.object(s.repo, 'fixtures', return_value={'cases': []}):
        assert s.intake(body, key) == created
        assert s.intake_attempt(key) == created
        error('IDEMPOTENCY_CONFLICT', 409, lambda: s.intake({**body, 'text': '다른 문의'}, key))
        error('INVALID_REFERENCE_CASE', 422, lambda: s.intake(body, str(uuid.uuid4())))
    assert len(s.list()['cases']) == 3


def test_distinct_keys_and_legacy_calls_remain_distinct(store):
    s = store()
    n = len(s.list()['cases'])
    results = [s.intake(BODY, str(uuid.uuid4())) for _ in range(2)] + [s.intake(BODY) for _ in range(2)]
    assert len({row['id'] for row in results}) == 4
    assert len(store().list()['cases']) == n + 4


def test_absent_and_invalid_keys_never_create_intake(store):
    s = store()
    n = len(s.list()['cases'])
    error('INTAKE_ATTEMPT_NOT_FOUND', 404, lambda: s.intake_attempt(str(uuid.uuid4())))
    for key in ['', 'not-a-uuid', str(uuid.uuid1()), 'x' * 1000, True]:
        error('INVALID_IDEMPOTENCY_KEY', 422, lambda: s.intake(BODY, key))
        error('INVALID_IDEMPOTENCY_KEY', 422, lambda: s.intake_attempt(key))
    assert len(s.list()['cases']) == n


def test_parallel_same_key_creates_once_and_input_conflict(store):
    s = store()
    n = len(s.list()['cases'])
    key = str(uuid.uuid4())
    barrier = Barrier(4)
    def create(_):
        service = store()
        barrier.wait(timeout=5)
        return service.intake(copy.deepcopy(BODY), key)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(create, range(4)))
    assert len({row['id'] for row in results}) == 1
    assert all(row['revision'] == 0 and len(row['history']) == 1 for row in results)
    assert len(s.list()['cases']) == n + 1
    error('IDEMPOTENCY_CONFLICT', 409, lambda: store().intake({**BODY, 'text': '변경'}, key))


@pytest.mark.parametrize('texts', [('합성 내용 하나', '합성 내용 둘'), ('같은 합성 내용', '같은 합성 내용')])
def test_cas_collision_creates_one(texts):
    backing = InMemoryCasStore()
    CasCaseRepository(backing).list()
    class RacingStore:
        def __init__(self):
            self.barrier, self.lock, self.writes = Barrier(2), Lock(), 0
        def read(self, key):
            return backing.read(key)
        def compare_and_swap(self, key, payload, expected):
            with self.lock:
                self.writes += 1
                wait = self.writes <= 2
            if wait:
                self.barrier.wait(timeout=5)
            return backing.compare_and_swap(key, payload, expected)
    race = RacingStore()
    key = str(uuid.uuid4())
    def run(text):
        try:
            return CaseService(CasCaseRepository(race), Mock()).intake({**BODY, 'text': text}, key)
        except DemoError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, texts))
    good = [r for r in results if isinstance(r, dict)]
    bad = [r for r in results if isinstance(r, DemoError)]
    if texts[0] == texts[1]:
        assert len(good) == 2 and not bad
        assert good[0] == good[1]
    else:
        assert len(good) == len(bad) == 1
        assert bad[0].code == 'IDEMPOTENCY_CONFLICT'
    assert len(CasCaseRepository(backing).list()) == 3


def test_cas_commit_then_timeout_is_recovered_without_second_write():
    backing = InMemoryCasStore()
    CasCaseRepository(backing).list()
    class LostResponse:
        writes = 0
        def read(self, key):
            return backing.read(key)
        def compare_and_swap(self, key, payload, expected):
            self.writes += 1
            backing.compare_and_swap(key, payload, expected)
            raise DemoError('STORAGE_TIMEOUT', '응답 유실 대조군', 503)
    lost = LostResponse()
    key = str(uuid.uuid4())
    s = CaseService(CasCaseRepository(lost), Mock())
    error('STORAGE_TIMEOUT', 503, lambda: s.intake(BODY, key))
    assert lost.writes == 1
    saved = s.intake_attempt(key)
    assert s.intake(BODY, key) == saved
    assert lost.writes == 1 and len(s.list()['cases']) == 3


def test_local_commit_then_error_can_be_looked_up(tmp_path):
    from server import repository
    repo = JsonCaseRepository(tmp_path / 'cases.json')
    repo.list()
    s = CaseService(repo, Mock())
    key = str(uuid.uuid4())
    original = repository.atomic_json
    def committed(path, document):
        original(path, document)
        raise OSError('synthetic response loss after write')
    with patch.object(repository, 'atomic_json', side_effect=committed):
        with pytest.raises(OSError):
            s.intake(BODY, key)
        saved = s.intake_attempt(key)
        assert s.intake(BODY, key) == saved
    assert len(repo.list()) == 3


@pytest.mark.parametrize('corruption', ['missing-case', 'null-entry'])
def test_corrupt_attempt_mapping_is_not_silently_recreated(corruption):
    backing = InMemoryCasStore()
    repo = CasCaseRepository(backing)
    s = CaseService(repo, Mock())
    key = str(uuid.uuid4())
    s.intake(BODY, key)
    value = backing.read(repo.key)
    for digest, record in value.payload['intakeRequests'].items():
        if corruption == 'missing-case':
            record['caseId'] = 'MISSING'
        else:
            value.payload['intakeRequests'][digest] = None
    backing.compare_and_swap(repo.key, value.payload, value.version)
    error('STORAGE_INVALID', 503, lambda: s.intake(BODY, key))
    error('STORAGE_INVALID', 503, lambda: s.intake_attempt(key))
    assert len(repo.list()) == 3


def test_http_create_retry_recovery_and_cors(tmp_path):
    from starlette.testclient import TestClient
    from server.app import create_app
    s = CaseService(JsonCaseRepository(tmp_path / 'http-cases.json'), Mock())
    key = str(uuid.uuid4())
    headers = {'X-Idempotency-Key': key}
    with patch('server.handlers.service', return_value=s), TestClient(create_app()) as client:
        assert client.get('/api/intake-attempts/' + key).status_code == 404
        first = client.post('/api/intake', json=BODY, headers=headers)
        assert first.status_code == 201, first.text
        second = client.post('/api/intake', json=BODY, headers=headers)
        assert second.status_code == 201 and second.json() == first.json()
        recover = client.get('/api/intake-attempts/' + key)
        assert recover.status_code == 200 and recover.json() == first.json()
        changed = client.post('/api/intake', json={**BODY, 'text': '다른 내용'}, headers=headers)
        assert changed.status_code == 409 and changed.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
        assert client.post('/api/intake', json=BODY, headers={'X-Idempotency-Key': ''}).status_code == 422
        assert client.get('/api/intake-attempts/invalid').status_code == 422
        preflight = client.options('/api/intake', headers={'Origin': 'http://localhost:3100',
            'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'X-Idempotency-Key'})
        assert preflight.status_code == 200, preflight.text
        assert 'X-Idempotency-Key' in preflight.headers['access-control-allow-headers']
    assert len(s.list()['cases']) == 3
