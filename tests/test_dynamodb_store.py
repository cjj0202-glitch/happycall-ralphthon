"""Offline AWS wire-contract and conditional-write tests; no SDK credentials."""
import copy
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from types import SimpleNamespace

import pytest

from server.cas_budget import CasBudget
from server.cas_store import CasConflict
from server.dynamodb_store import DynamoDbCasStore, DynamoDbStoreError, MAX_DOCUMENT_BYTES
from server.errors import DemoError

KEY = "oneflow/cases.json"
METADATA = {"HTTPStatusCode": 200}


class AwsError(Exception):
    def __init__(self, code, status=400):
        super().__init__("PRIVATE-PAYLOAD SECRET-CREDENTIAL")
        self.response = {"Error": {"Code": code}, "ResponseMetadata": {"HTTPStatusCode": status}}


class FakeDynamo:
    """Independent item store implementing the two AWS conditions we permit."""
    def __init__(self):
        self.items, self.gets, self.puts = {}, [], []
        self.lock = Lock()

    def get_item(self, **request):
        with self.lock:
            self.gets.append(copy.deepcopy(request))
            assert request["ConsistentRead"] is True
            item = self.items.get(request["Key"]["pk"]["S"])
            return {"ResponseMetadata": METADATA, **({"Item": copy.deepcopy(item)} if item else {})}

    def put_item(self, **request):
        with self.lock:
            self.puts.append(copy.deepcopy(request))
            key = request["Item"]["pk"]["S"]
            current = self.items.get(key)
            condition = request.get("ConditionExpression")
            if condition == "attribute_not_exists(#pk)":
                assert request["ExpressionAttributeNames"] == {"#pk": "pk"}
                matches = current is None
            elif condition == "#version = :expected":
                assert request["ExpressionAttributeNames"] == {"#version": "version"}
                matches = current is not None and current["version"] == request["ExpressionAttributeValues"][":expected"]
            else:
                raise AssertionError("unconditional or unsupported write")
            if not matches:
                raise AwsError("ConditionalCheckFailedException")
            self.items[key] = copy.deepcopy(request["Item"])
            return {"ResponseMetadata": METADATA}


def adapter(client=None):
    return DynamoDbCasStore(table_name="happycall-offline", client=client or FakeDynamo())


def test_roundtrip_consistent_read_versions_and_source_copy():
    client = FakeDynamo()
    store = adapter(client)
    assert store.read(KEY) is None
    payload = {"cases": [{"id": "synthetic", "revision": 4, "text": "합성", "n": None}], "amount": 2.5}
    before = copy.deepcopy(payload)
    version = store.compare_and_swap(KEY, payload, None)
    actual = store.read(KEY)
    assert actual.payload == before == payload and actual.version == version
    assert len(version) == 32
    assert client.gets[-1] == {"TableName": "happycall-offline", "Key": {"pk": {"S": KEY}}, "ConsistentRead": True}
    assert client.puts[-1]["ReturnValues"] == "NONE"
    actual.payload["cases"][0]["text"] = "local change"
    assert store.read(KEY).payload == before
    next_version = store.compare_and_swap(KEY, {"cases": []}, version)
    assert next_version != version and store.read(KEY).version == next_version


def test_existing_create_and_stale_version_never_overwrite():
    store = adapter()
    first = store.compare_and_swap(KEY, {"n": 1}, None)
    with pytest.raises(CasConflict):
        store.compare_and_swap(KEY, {"n": 0}, None)
    second = store.compare_and_swap(KEY, {"n": 2}, first)
    with pytest.raises(CasConflict):
        store.compare_and_swap(KEY, {"n": 3}, first)
    assert store.read(KEY).payload == {"n": 2} and store.read(KEY).version == second


def test_two_instances_racing_on_same_version_have_exactly_one_winner():
    client = FakeDynamo()
    stores = [adapter(client), adapter(client)]
    version = stores[0].compare_and_swap(KEY, {"n": 0}, None)
    barrier = Barrier(2)

    def write(index):
        observed = stores[index].read(KEY)
        assert observed.version == version
        barrier.wait(timeout=5)
        try:
            stores[index].compare_and_swap(KEY, {"n": index + 1}, observed.version)
            return "saved"
        except CasConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(write, [0, 1])) == ["conflict", "saved"]
    assert stores[0].read(KEY).payload["n"] in (1, 2)


def test_shared_budget_preserves_baseline_and_exact_limit():
    client = FakeDynamo()
    first = CasBudget(adapter(client), initial_reserved_cents=2985)
    second = CasBudget(adapter(client), initial_reserved_cents=2985)
    assert first.status()["reservedUsd"] == 29.85
    first.reserve(15, "synthetic")
    with pytest.raises(DemoError) as caught:
        second.reserve(1, "synthetic")
    assert caught.value.code == "BUDGET_LIMIT" and second.status()["reservedUsd"] == 30


def test_successful_write_with_lost_response_is_uncertain_and_not_retried():
    class Lost(FakeDynamo):
        def put_item(self, **request):
            super().put_item(**request)
            raise TimeoutError("SECRET-CREDENTIAL")

    client = Lost()
    store = adapter(client)
    with pytest.raises(DynamoDbStoreError) as caught:
        store.compare_and_swap(KEY, {"n": 1}, None)
    assert caught.value.write_uncertain and "SECRET" not in str(caught.value)
    assert len(client.puts) == 1 and store.read(KEY).payload == {"n": 1}


@pytest.mark.parametrize("code", ["AccessDeniedException", "ResourceNotFoundException", "ThrottlingException"])
def test_service_errors_never_become_absence_or_cas_conflict(code):
    class Failed(FakeDynamo):
        def get_item(self, **request):
            raise AwsError(code)

        def put_item(self, **request):
            raise AwsError(code)

    store = adapter(Failed())
    with pytest.raises(DynamoDbStoreError, match="DYNAMODB_READ_FAILED"):
        store.read(KEY)
    with pytest.raises(DynamoDbStoreError, match="DYNAMODB_WRITE_UNCERTAIN"):
        store.compare_and_swap(KEY, {}, None)


@pytest.mark.parametrize("payload", [{1: "bad-key"}, {"n": float("nan")}, {"text": "x" * MAX_DOCUMENT_BYTES},
                                     {"text": "한" * (MAX_DOCUMENT_BYTES // 3)}])
def test_invalid_or_oversized_documents_fail_before_transport(payload):
    client = FakeDynamo()
    with pytest.raises(DynamoDbStoreError):
        adapter(client).compare_and_swap(KEY, payload, None)
    assert client.puts == [] and client.gets == []


def test_document_size_boundary_includes_serialized_utf8_bytes():
    client = FakeDynamo()
    store = adapter(client)
    payload = {"s": "x" * (MAX_DOCUMENT_BYTES - len('{"s":""}'))}
    version = store.compare_and_swap(KEY, payload, None)
    assert len(client.items[KEY]["payload"]["S"].encode("utf-8")) == MAX_DOCUMENT_BYTES
    payload["s"] += "x"
    with pytest.raises(DynamoDbStoreError, match="DYNAMODB_DOCUMENT_TOO_LARGE"):
        store.compare_and_swap(KEY, payload, version)
    assert len(client.puts) == 1


@pytest.mark.parametrize("raw", ['{"n":1,"n":2}', '{"n":NaN}', '[]'])
def test_corrupt_remote_json_is_not_missing(raw):
    client = FakeDynamo()
    client.items[KEY] = {"pk": {"S": KEY}, "version": {"S": "a" * 32}, "payload": {"S": raw}}
    with pytest.raises(DynamoDbStoreError, match="DYNAMODB_INVALID_RESPONSE"):
        adapter(client).read(KEY)


def test_key_version_and_response_validation():
    client = FakeDynamo()
    store = adapter(client)
    for key in ("other/cases.json", "oneflow/../cases.json"):
        with pytest.raises(DynamoDbStoreError):
            store.read(key)
    with pytest.raises(DynamoDbStoreError, match="DYNAMODB_INVALID_VERSION"):
        store.compare_and_swap(KEY, {}, "old-version")
    assert client.puts == [] and client.gets == []
    client.items[KEY] = {"pk": {"S": "wrong"}, "version": {"S": "a" * 32}, "payload": {"S": "{}"}}
    with pytest.raises(DynamoDbStoreError, match="DYNAMODB_INVALID_RESPONSE"):
        store.read(KEY)


def test_sdk_is_lazy_and_automatic_retries_are_disabled(monkeypatch):
    calls = []
    client = FakeDynamo()

    def configuration(**kwargs):
        calls.append(("config", kwargs))
        return kwargs

    def build_client(service, **kwargs):
        calls.append((service, kwargs))
        return client

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=build_client))
    monkeypatch.setitem(sys.modules, "botocore.config", SimpleNamespace(Config=configuration))
    store = DynamoDbCasStore(table_name="happycall-offline")
    assert calls == []
    assert store.read(KEY) is None
    assert calls[0][1]["retries"] == {"total_max_attempts": 1, "mode": "standard"}
    assert calls[1][0] == "dynamodb"
