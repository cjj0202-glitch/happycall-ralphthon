"""Private Blob protocol tests: synthetic MockTransport only, no credentials/network."""
import json
import logging
import traceback
from uuid import UUID

import httpx
import pytest

from server.cas_store import CasConflict, CasValue
from server.vercel_blob_store import BlobStoreError, VercelBlobCasStore


TOKEN = "synthetic-only-no-credential"
STORE = "Synthetic123"
KEY = "oneflow/cases.json"
ETAG = '"opaque-Etag,with-comma"'


@pytest.fixture
def make_store():
    stores = []

    def factory(handler, **kwargs):
        settings = {"token": TOKEN, "store_id": "store_" + STORE, **kwargs}
        store = VercelBlobCasStore(transport=httpx.MockTransport(handler), **settings)
        stores.append(store)
        return store

    yield factory
    for store in stores:
        store.close()


def success(*, etag=ETAG, pathname=KEY, status=200):
    return httpx.Response(status, json={"pathname": pathname, "etag": etag})


def test_read_origin_cache_bypass_and_body_etag_are_one_response(make_store):
    requests = []

    def respond(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.url == f"https://{STORE.lower()}.private.blob.vercel-storage.com/{KEY}?cache=0"
        assert request.headers["authorization"] == "Bearer " + TOKEN
        assert request.headers["accept-encoding"] == "identity"
        assert "if-none-match" not in request.headers
        version = '"first"' if len(requests) == 1 else '"second"'
        return httpx.Response(200, json={"revision": len(requests)}, headers={"ETag": version})

    store = make_store(respond)
    assert store.read(KEY) == CasValue({"revision": 1}, '"first"')
    assert store.read(KEY) == CasValue({"revision": 2}, '"second"')
    assert len(requests) == 2  # No HEAD, cached copy or second ETag fetch.


@pytest.mark.parametrize("expected", [None, ETAG])
@pytest.mark.parametrize("status", [200, 201])
def test_create_or_update_is_one_exact_conditional_put(make_store, expected, status):
    requests = []
    payload = {"text": "합성 문의", "revision": 0, "empty": None}

    def respond(request):
        requests.append(request)
        assert request.method == "PUT"
        assert request.url == "https://vercel.com/api/blob/?pathname=oneflow%2Fcases.json"
        headers = request.headers
        assert headers["authorization"] == "Bearer " + TOKEN
        assert headers["x-api-version"] == "12"
        assert headers["x-vercel-blob-store-id"] == STORE
        assert headers["x-vercel-blob-access"] == "private"
        assert headers["x-content-type"] == "application/json"
        assert headers["content-type"] == "application/json"
        assert headers["x-add-random-suffix"] == "0"
        assert headers["x-api-blob-request-attempt"] == "0"
        UUID(headers["x-api-blob-request-id"])
        assert headers["x-allow-overwrite"] == ("0" if expected is None else "1")
        if expected is None:
            assert "x-if-match" not in headers
        else:
            assert headers["x-if-match"] == expected
        assert "if-match" not in headers
        assert int(headers["content-length"]) == len(request.content)
        assert json.loads(request.content) == payload
        return success(etag='"new-version"', status=status)

    store = make_store(respond)
    assert store.compare_and_swap(KEY, payload, expected) == '"new-version"'
    assert len(requests) == 1


def test_same_payload_and_same_etag_is_still_confirmed_success(make_store):
    store = make_store(lambda request: success())
    assert store.compare_and_swap(KEY, {"unchanged": True}, ETAG) == ETAG


def test_only_remote_404_is_absence(make_store):
    store = make_store(lambda request: httpx.Response(404, content=b"not found"))
    assert store.read(KEY) is None


@pytest.mark.parametrize("status", [201, 204, 206, 301, 302, 304, 307, 308, 400, 401, 403, 409, 412, 429, 500, 502, 503])
def test_read_non_200_non_404_is_error_not_absence(make_store, status):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            status, json={"error": {"code": "precondition_failed"}},
            headers={"location": "https://unexpected.invalid/", "etag": ETAG},
        )

    with pytest.raises(BlobStoreError) as caught:
        make_store(respond).read(KEY)
    assert caught.value.status_code == status
    assert not caught.value.write_uncertain
    assert len(requests) == 1


def test_only_confirmed_precondition_failure_is_cas_conflict(make_store):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(412, json={"error": {"code": "precondition_failed"}})

    with pytest.raises(CasConflict):
        make_store(respond).compare_and_swap(KEY, {}, ETAG)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "status,body",
    [
        (400, {"error": {"code": "bad_request", "message": "already exists"}}),
        (409, {"error": {"code": "already_exists"}}),
        (400, {"error": {"code": "precondition_failed"}}),
        (409, {"error": {"code": "precondition_failed"}}),
        (403, {"error": {"code": "precondition_failed"}}),
        (429, {"error": {"code": "precondition_failed"}}),
        (500, {"error": {"code": "precondition_failed"}}),
        (412, {}), (412, {"code": "precondition_failed"}),
        (412, {"error": "precondition_failed"}),
        (412, {"error": {"code": "bad_request"}}),
        (404, {"error": {"code": "not_found"}}),
        (401, {"error": {"code": "forbidden"}}),
        (503, {"error": {"code": "unknown_error"}}),
        (307, {"error": {"code": "precondition_failed"}}),
    ],
)
def test_uncertain_put_errors_are_not_conflicts_or_retried(make_store, status, body):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, json=body, headers={"location": "https://unexpected.invalid/"})

    with pytest.raises(BlobStoreError) as caught:
        make_store(respond).compare_and_swap(KEY, {}, None)
    assert caught.value.status_code == status
    assert caught.value.write_uncertain
    assert len(requests) == 1


@pytest.mark.parametrize("body", [b"", b"<html>denied</html>", b"null", b"[]", b'{"error":{"code":"precondition_failed","code":"bad_request"}}'])
def test_malformed_412_body_is_not_a_conflict(make_store, body):
    with pytest.raises(BlobStoreError) as caught:
        make_store(lambda request: httpx.Response(412, content=body)).compare_and_swap(KEY, {}, ETAG)
    assert caught.value.status_code == 412


@pytest.mark.parametrize("method", ["read", "write"])
@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteError, httpx.RemoteProtocolError])
def test_network_error_is_sanitized_no_retry_or_success_guess(make_store, method, error_type, caplog):
    requests = []
    sensitive = "private-original-payload-" + TOKEN

    def respond(request):
        requests.append(request)
        raise error_type(f"{request.url} {sensitive}", request=request)

    caplog.set_level(logging.DEBUG)
    store = make_store(respond)
    with pytest.raises(BlobStoreError) as caught:
        if method == "read":
            store.read(KEY)
        else:
            store.compare_and_swap(KEY, {"text": sensitive}, ETAG)
    formatted = "".join(traceback.format_exception(caught.value))
    assert sensitive not in formatted + caplog.text
    assert TOKEN not in formatted + caplog.text
    assert "https://" not in str(caught.value)
    assert caught.value.code == "BLOB_TRANSPORT_ERROR"
    assert caught.value.write_uncertain == (method == "write")
    assert len(requests) == 1


@pytest.mark.parametrize("etag", [None, "", "abc", '""', '*', 'W/"weak"', '"first", "second"', '"bad\r\nheader"', '"bad\x00header"', '"한글"', '"' + "a" * 257 + '"'])
def test_missing_or_invalid_response_etag_is_error(make_store, etag):
    headers = {} if etag is None else {"etag": etag}
    # Non-ASCII header encoding is rejected by httpx before it reaches the adapter;
    # the transport-error path must remain safe as well.
    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, content=b"{}", headers=headers)
        return success(etag=etag)

    store = make_store(respond)
    with pytest.raises(BlobStoreError):
        store.read(KEY)
    with pytest.raises(BlobStoreError) as caught:
        store.compare_and_swap(KEY, {}, None)
    assert caught.value.code == "BLOB_INVALID_ETAG"
    assert caught.value.write_uncertain


@pytest.mark.parametrize("expected", ["", "*", "unquoted", 'W/"weak"', '"bad\n"', 1, False])
def test_invalid_expected_etag_never_reaches_network(make_store, expected):
    requests = []
    store = make_store(lambda request: requests.append(request))
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_ETAG"):
        store.compare_and_swap(KEY, {}, expected)
    assert requests == []


@pytest.mark.parametrize("key", ["", "oneflow", "other/cases.json", "oneflow2/cases.json", "oneflow/../cases.json", "oneflow/./cases.json", "oneflow//cases.json", "oneflow/", "/oneflow/cases.json", "oneflow\\cases.json", "https://evil.invalid/oneflow/cases.json", "oneflow/%2e%2e/cases.json", "oneflow/cases.json?token=x", "oneflow/cases.json#x", "oneflow/my case.json", "oneflow/한글.json", "oneflow/\n.json", None, 1])
def test_key_validation_precedes_network_and_token_provider(make_store, key):
    calls = []
    store = make_store(lambda request: calls.append("network"), token=lambda: calls.append("token"))
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_KEY"):
        store.read(key)
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_KEY"):
        store.compare_and_swap(key, {}, None)
    assert calls == []


def test_explicit_nested_namespace_is_enforced(make_store):
    key = "oneflow/v1/cases.json"
    store = make_store(lambda request: success(pathname=key), namespace="oneflow/v1")
    assert store.compare_and_swap(key, {}, None) == ETAG
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_KEY"):
        store.read(KEY)


@pytest.mark.parametrize("settings", [{"store_id": ""}, {"store_id": "store_"}, {"store_id": "example.com"}, {"store_id": "a@evil.invalid"}, {"store_id": "a:443"}, {"store_id": "a/b"}, {"store_id": None}, {"namespace": "../oneflow"}, {"namespace": "oneflow/"}, {"timeout_seconds": 0}, {"timeout_seconds": float("nan")}, {"timeout_seconds": True}, {"max_document_bytes": 0}, {"max_document_bytes": True}, {"max_document_bytes": 4 * 1024 * 1024 + 1}])
def test_invalid_configuration_is_sanitized(make_store, settings):
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_CONFIGURATION"):
        make_store(lambda request: success(), **settings)


@pytest.mark.parametrize("token", ["", " token", "bad\nheader", "한글", None, 1])
def test_invalid_credentials_fail_before_network(make_store, token):
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_CREDENTIAL"):
        make_store(lambda request: success(), token=token)


def test_credentials_are_refreshed_once_per_request_and_never_read_from_environment(make_store, monkeypatch):
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "must-not-use-this")
    calls = []
    requests = []

    def token_provider():
        calls.append(True)
        return f"synthetic-{len(calls)}"

    def respond(request):
        requests.append(request)
        assert request.headers["authorization"] == f"Bearer synthetic-{len(requests)}"
        return httpx.Response(200, json={}, headers={"etag": ETAG})

    store = make_store(respond, token=token_provider)
    store.read(KEY)
    store.read(KEY)
    assert len(calls) == len(requests) == 2


def test_credential_provider_exception_is_sanitized(make_store):
    calls = []

    def provider():
        raise RuntimeError(TOKEN)

    with pytest.raises(BlobStoreError) as caught:
        make_store(lambda request: calls.append(request), token=provider).read(KEY)
    assert caught.value.code == "BLOB_CREDENTIAL_UNAVAILABLE"
    assert TOKEN not in "".join(traceback.format_exception(caught.value))
    assert calls == []


@pytest.mark.parametrize("raw", [b"", b"<html/>", b"[]", b"null", b"1", b'"string"', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}', b'{"x":"\\ud800"}', b'\xff', b'{"broken":'])
def test_invalid_json_document_is_not_initialized_as_empty(make_store, raw):
    store = make_store(lambda request: httpx.Response(200, content=raw, headers={"etag": ETAG}))
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_JSON"):
        store.read(KEY)


@pytest.mark.parametrize("payload", [None, [], {"x": float("nan")}, {"x": float("inf")}, {1: "key"}, {"x": object()}, {"x": (1, 2)}, {"x": "\ud800"}])
def test_invalid_payload_fails_without_network(make_store, payload):
    calls = []
    store = make_store(lambda request: calls.append(request))
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_JSON"):
        store.compare_and_swap(KEY, payload, None)
    assert calls == []


def test_cyclic_payload_fails_without_network(make_store):
    calls = []
    payload = {}
    payload["cycle"] = payload
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_JSON"):
        make_store(lambda request: calls.append(request)).compare_and_swap(KEY, payload, None)
    assert calls == []


@pytest.mark.parametrize("raw", [b"", b"[]", b"null", b'{"etag":"\\"a\\"","etag":"\\"b\\""}'])
def test_invalid_success_metadata_keeps_write_uncertainty(make_store, raw):
    with pytest.raises(BlobStoreError) as caught:
        make_store(lambda request: httpx.Response(200, content=raw)).compare_and_swap(KEY, {}, None)
    assert caught.value.code == "BLOB_INVALID_JSON"
    assert caught.value.write_uncertain


@pytest.mark.parametrize("pathname", [None, "other/cases.json", "oneflow/cases-random.json", "oneflow%2Fcases.json", "https://evil.invalid/oneflow/cases.json"])
def test_success_metadata_must_match_exact_requested_key(make_store, pathname):
    with pytest.raises(BlobStoreError, match="BLOB_PATH_MISMATCH") as caught:
        make_store(lambda request: success(pathname=pathname)).compare_and_swap(KEY, {}, None)
    assert caught.value.write_uncertain


def test_raw_error_response_never_enters_exception_or_logs(make_store, caplog):
    caplog.set_level(logging.DEBUG)
    sensitive = "original-user-text-" + TOKEN
    body = {"error": {"code": sensitive, "message": sensitive}}
    store = make_store(lambda request: httpx.Response(400, json=body))
    with pytest.raises(BlobStoreError) as caught:
        store.compare_and_swap(KEY, {"text": sensitive}, None)
    assert sensitive not in str(caught.value) + repr(caught.value) + caplog.text
    assert TOKEN not in str(caught.value) + repr(caught.value) + caplog.text


def test_document_size_boundary_uses_utf8_bytes(make_store):
    payload = {"text": "가"}
    size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    calls = []

    def respond(request):
        calls.append(request)
        return success()

    assert make_store(respond, max_document_bytes=size).compare_and_swap(KEY, payload, None) == ETAG
    with pytest.raises(BlobStoreError, match="BLOB_DOCUMENT_TOO_LARGE"):
        make_store(respond, max_document_bytes=size - 1).compare_and_swap(KEY, payload, None)
    assert len(calls) == 1


class Chunks(httpx.SyncByteStream):
    def __init__(self, *chunks):
        self.chunks = chunks
        self.read_count = 0
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            self.read_count += 1
            yield chunk

    def close(self):
        self.closed = True


def test_streaming_size_limit_without_content_length_closes_early(make_store):
    stream = Chunks(b"{" * 8, b"x" * 8, b"must-not-be-read")
    store = make_store(lambda request: httpx.Response(200, stream=stream, headers={"etag": ETAG}), max_document_bytes=8)
    with pytest.raises(BlobStoreError, match="BLOB_RESPONSE_TOO_LARGE"):
        store.read(KEY)
    assert stream.read_count == 2
    assert stream.closed


def test_content_length_limit_precedes_reading_response(make_store):
    stream = Chunks(b"must-not-be-read")
    store = make_store(lambda request: httpx.Response(200, stream=stream, headers={"etag": ETAG, "content-length": "9"}), max_document_bytes=8)
    with pytest.raises(BlobStoreError, match="BLOB_RESPONSE_TOO_LARGE"):
        store.read(KEY)
    assert stream.read_count == 0
    assert stream.closed


@pytest.mark.parametrize("length", ["-1", "bad", "1, 1"])
def test_invalid_content_length_is_not_accepted(make_store, length):
    store = make_store(lambda request: httpx.Response(200, content=b"{}", headers={"etag": ETAG, "content-length": length}))
    with pytest.raises(BlobStoreError, match="BLOB_INVALID_RESPONSE"):
        store.read(KEY)


def test_read_exact_size_limit_is_accepted(make_store):
    store = make_store(lambda request: httpx.Response(200, content=b"{}", headers={"etag": ETAG}), max_document_bytes=2)
    assert store.read(KEY) == CasValue({}, ETAG)


def test_put_metadata_size_limit_and_write_uncertainty(make_store):
    store = make_store(lambda request: httpx.Response(200, content=b"x" * (64 * 1024 + 1)))
    with pytest.raises(BlobStoreError, match="BLOB_RESPONSE_TOO_LARGE") as caught:
        store.compare_and_swap(KEY, {}, None)
    assert caught.value.write_uncertain
