"""Small private JSON documents using the pinned Vercel Blob v12 protocol.

Compatibility basis: @vercel/blob 2.8.0, source 8817cbad75d009fedebd33fb46748c2c0200ea46.
No retries: only a confirmed 412/precondition_failed is safe for the CAS caller
to retry. Remote create races and deployment durability require live validation.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx

from server.cas_store import CasConflict, CasValue


_API_URL = "https://vercel.com/api/blob/"
_MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
_MAX_METADATA_BYTES = 64 * 1024
_SEGMENT = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}\Z")
_STORE_ID = re.compile(r"[A-Za-z0-9]{1,63}\Z")
_ETAG = re.compile(r'"[\x21\x23-\x7e]{1,256}"\Z')


class BlobStoreError(RuntimeError):
    """Sanitized storage failure; no request, response, credentials or payload."""

    def __init__(
        self, code: str, *, status_code: int | None = None, write_uncertain: bool = False
    ):
        self.code = code
        self.status_code = status_code
        self.write_uncertain = write_uncertain
        suffix = f" (HTTP {status_code})" if status_code is not None else ""
        super().__init__(code + suffix)


def _valid_path(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= 1024
        and all(_SEGMENT.fullmatch(segment) for segment in value.split("/"))
    )


def _valid_etag(value: Any) -> bool:
    # Strong validators only. Preserve the quotes and opaque content exactly.
    return isinstance(value, str) and bool(_ETAG.fullmatch(value))


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON value")


def _validate_json_value(value: Any, ancestors: set[int] | None = None) -> None:
    """Reject coercions (e.g. integer keys), non-finite numbers and lone surrogates."""
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, str):
        value.encode("utf-8")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite JSON value")
        return
    if not isinstance(value, (dict, list)):
        raise ValueError("Not a JSON value")
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        raise ValueError("Cyclic JSON value")
    ancestors.add(id(value))
    try:
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str):
                    raise ValueError("Not a JSON member name")
                key.encode("utf-8")
                _validate_json_value(child, ancestors)
        else:
            for child in value:
                _validate_json_value(child, ancestors)
    finally:
        ancestors.remove(id(value))


def _parse_object(raw: bytes, *, write_uncertain: bool = False) -> dict:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
        if not isinstance(value, dict):
            raise ValueError("Expected JSON object")
        _validate_json_value(value)
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise BlobStoreError("BLOB_INVALID_JSON", write_uncertain=write_uncertain) from None
    return value


class VercelBlobCasStore:
    """Synchronous CAS transport with explicit credentials and a private origin.

    A token callable is evaluated once per request (OIDC refresh is caller-owned).
    ``transport`` is a trusted test seam; use MockTransport, not a retrying wrapper.
    """

    def __init__(
        self,
        *,
        token: str | Callable[[], str],
        store_id: str,
        namespace: str = "oneflow",
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 10.0,
        max_document_bytes: int = _MAX_DOCUMENT_BYTES,
    ):
        if not isinstance(store_id, str):
            raise BlobStoreError("BLOB_INVALID_CONFIGURATION")
        bare_id = store_id.removeprefix("store_")
        if not _STORE_ID.fullmatch(bare_id) or not _valid_path(namespace):
            raise BlobStoreError("BLOB_INVALID_CONFIGURATION")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 60
            or isinstance(max_document_bytes, bool)
            or not isinstance(max_document_bytes, int)
            or not 0 < max_document_bytes <= _MAX_DOCUMENT_BYTES
        ):
            raise BlobStoreError("BLOB_INVALID_CONFIGURATION")
        if not callable(token):
            self._validate_token(token)
        self._token = token
        self._store_id = bare_id
        self._namespace = namespace + "/"
        self._origin = f"https://{bare_id}.private.blob.vercel-storage.com/"
        self._max_document_bytes = max_document_bytes
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            headers={"Accept-Encoding": "identity"},
        )

    @staticmethod
    def _validate_token(token: Any) -> str:
        if (
            not isinstance(token, str)
            or not 0 < len(token) <= 8192
            or any(not 33 <= ord(char) <= 126 for char in token)
        ):
            raise BlobStoreError("BLOB_INVALID_CREDENTIAL")
        return token

    def _authorization(self) -> str:
        try:
            token = self._token() if callable(self._token) else self._token
        except Exception:
            raise BlobStoreError("BLOB_CREDENTIAL_UNAVAILABLE") from None
        return "Bearer " + self._validate_token(token)

    def _check_key(self, key: str) -> None:
        if not _valid_path(key) or not key.startswith(self._namespace):
            raise BlobStoreError("BLOB_INVALID_KEY")

    def _request(
        self, method: str, url: str, *, headers: dict, limit: int, **kwargs: Any
    ) -> tuple[int, httpx.Headers, bytes]:
        # Do not use raise_for_status: httpx exceptions include the request URL.
        is_write = method == "PUT"
        headers = {**headers, "Authorization": self._authorization()}
        try:
            with self._client.stream(
                method, url, headers=headers, follow_redirects=False, **kwargs
            ) as response:
                length = response.headers.get("content-length")
                if length is not None:
                    if not length.isascii() or not length.isdecimal():
                        raise BlobStoreError(
                            "BLOB_INVALID_RESPONSE", write_uncertain=is_write
                        )
                    if int(length) > limit:
                        raise BlobStoreError("BLOB_RESPONSE_TOO_LARGE", write_uncertain=is_write)
                raw = bytearray()
                for chunk in response.iter_bytes():
                    if len(raw) + len(chunk) > limit:
                        raise BlobStoreError("BLOB_RESPONSE_TOO_LARGE", write_uncertain=is_write)
                    raw.extend(chunk)
                return response.status_code, response.headers, bytes(raw)
        except BlobStoreError:
            raise
        except Exception:
            # A request/response exception may contain credentials, URL or body.
            # Never convert this uncertainty into a version conflict or retry.
            raise BlobStoreError("BLOB_TRANSPORT_ERROR", write_uncertain=is_write) from None

    def read(self, key: str) -> CasValue | None:
        self._check_key(key)
        status, headers, raw = self._request(
            "GET",
            self._origin + key,
            params={"cache": "0"},
            headers={},
            limit=self._max_document_bytes,
        )
        if status == 404:
            return None
        if status != 200:
            raise BlobStoreError("BLOB_HTTP_ERROR", status_code=status)
        etag = headers.get("etag")
        if not _valid_etag(etag):
            raise BlobStoreError("BLOB_INVALID_ETAG")
        return CasValue(payload=_parse_object(raw), version=etag)

    def compare_and_swap(
        self, key: str, payload: dict, expected_version: str | None
    ) -> str:
        self._check_key(key)
        if expected_version is not None and not _valid_etag(expected_version):
            raise BlobStoreError("BLOB_INVALID_ETAG")
        try:
            if not isinstance(payload, dict):
                raise ValueError("Expected JSON object")
            _validate_json_value(payload)
            raw = json.dumps(
                payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode("utf-8")
        except (ValueError, TypeError, RecursionError, OverflowError):
            raise BlobStoreError("BLOB_INVALID_JSON") from None
        if len(raw) > self._max_document_bytes:
            raise BlobStoreError("BLOB_DOCUMENT_TOO_LARGE")
        headers = {
            "Content-Type": "application/json",
            "x-vercel-blob-store-id": self._store_id,
            "x-api-version": "12",
            "x-vercel-blob-access": "private",
            "x-content-type": "application/json",
            "x-add-random-suffix": "0",
            "x-allow-overwrite": "0" if expected_version is None else "1",
            "x-api-blob-request-id": str(uuid4()),
            "x-api-blob-request-attempt": "0",
        }
        if expected_version is not None:
            headers["x-if-match"] = expected_version
        status, _, response_raw = self._request(
            "PUT",
            _API_URL,
            params={"pathname": key},
            headers=headers,
            content=raw,
            limit=_MAX_METADATA_BYTES,
        )
        if status == 412:
            try:
                error = _parse_object(response_raw, write_uncertain=True).get("error")
            except BlobStoreError:
                error = None
            if isinstance(error, dict) and error.get("code") == "precondition_failed":
                raise CasConflict() from None
        if status not in (200, 201):
            raise BlobStoreError("BLOB_HTTP_ERROR", status_code=status, write_uncertain=True)
        metadata = _parse_object(response_raw, write_uncertain=True)
        if metadata.get("pathname") != key:
            raise BlobStoreError("BLOB_PATH_MISMATCH", write_uncertain=True)
        etag = metadata.get("etag")
        if not _valid_etag(etag):
            raise BlobStoreError("BLOB_INVALID_ETAG", write_uncertain=True)
        return etag

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> VercelBlobCasStore:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
