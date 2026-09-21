"""Small JSON documents using DynamoDB strongly consistent reads and CAS puts.

Table partition key: pk (String). Credentials use the SDK's standard chain.
The Lambda-provided boto3 SDK is imported only when an actual request is made.
"""
from __future__ import annotations

import json
import re
from uuid import uuid4

from server.cas_store import CasConflict, CasValue
from server.vercel_blob_store import _object_pairs, _reject_constant, _valid_path, _validate_json_value

# Leave room below DynamoDB's 400 KiB item limit for key/version/attribute names.
MAX_DOCUMENT_BYTES = 350 * 1024
TABLE_NAME = re.compile(r"[A-Za-z0-9_.-]{3,255}\Z")
VERSION = re.compile(r"[a-f0-9]{32}\Z")


class DynamoDbStoreError(RuntimeError):
    def __init__(self, code, *, write_uncertain=False):
        self.code, self.write_uncertain = code, write_uncertain
        super().__init__(code)


def encode_document(payload):
    try:
        if not isinstance(payload, dict):
            raise ValueError
        _validate_json_value(payload)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > MAX_DOCUMENT_BYTES:
            raise DynamoDbStoreError("DYNAMODB_DOCUMENT_TOO_LARGE")
        return encoded
    except DynamoDbStoreError:
        raise
    except Exception:
        raise DynamoDbStoreError("DYNAMODB_INVALID_JSON") from None


class DynamoDbCasStore:
    def __init__(self, *, table_name, client=None):
        if not isinstance(table_name, str) or not TABLE_NAME.fullmatch(table_name):
            raise DynamoDbStoreError("DYNAMODB_INVALID_CONFIGURATION")
        self._table_name, self._client = table_name, client
        self._owned_client = client is None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config

                self._client = boto3.client("dynamodb", config=Config(
                    connect_timeout=5, read_timeout=10,
                    retries={"total_max_attempts": 1, "mode": "standard"}))
            except Exception:
                raise DynamoDbStoreError("DYNAMODB_CLIENT_UNAVAILABLE") from None
        return self._client

    @staticmethod
    def _key(key):
        if not _valid_path(key) or not key.startswith("oneflow/"):
            raise DynamoDbStoreError("DYNAMODB_INVALID_KEY")
        return {"pk": {"S": key}}

    @staticmethod
    def _ok(response):
        return (isinstance(response, dict)
                and isinstance(response.get("ResponseMetadata"), dict)
                and response["ResponseMetadata"].get("HTTPStatusCode") == 200)

    def read(self, key):
        request_key = self._key(key)
        try:
            response = self._get_client().get_item(
                TableName=self._table_name, Key=request_key, ConsistentRead=True)
        except Exception:
            raise DynamoDbStoreError("DYNAMODB_READ_FAILED") from None
        try:
            if not self._ok(response):
                raise ValueError
            if "Item" not in response:
                return None
            item = response["Item"]
            if (not isinstance(item, dict) or item.get("pk") != request_key["pk"]
                    or not isinstance(item.get("version"), dict)
                    or set(item["version"]) != {"S"}
                    or not isinstance(item["version"]["S"], str)
                    or not VERSION.fullmatch(item["version"]["S"])
                    or not isinstance(item.get("payload"), dict) or set(item["payload"]) != {"S"}
                    or not isinstance(item["payload"]["S"], str)):
                raise ValueError
            raw = item["payload"]["S"]
            if len(raw.encode("utf-8")) > MAX_DOCUMENT_BYTES:
                raise ValueError
            payload = json.loads(raw, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
            encode_document(payload)
            return CasValue(payload, item["version"]["S"])
        except Exception:
            raise DynamoDbStoreError("DYNAMODB_INVALID_RESPONSE") from None

    def compare_and_swap(self, key, payload, expected_version):
        request_key = self._key(key)
        if expected_version is not None and (not isinstance(expected_version, str)
                                            or not VERSION.fullmatch(expected_version)):
            raise DynamoDbStoreError("DYNAMODB_INVALID_VERSION")
        document = encode_document(payload)
        version = uuid4().hex
        request = {"TableName": self._table_name,
                   "Item": {**request_key, "payload": {"S": document}, "version": {"S": version}},
                   "ReturnValues": "NONE"}
        if expected_version is None:
            request.update(ConditionExpression="attribute_not_exists(#pk)",
                           ExpressionAttributeNames={"#pk": "pk"})
        else:
            request.update(ConditionExpression="#version = :expected",
                           ExpressionAttributeNames={"#version": "version"},
                           ExpressionAttributeValues={":expected": {"S": expected_version}})
        try:
            response = self._get_client().put_item(**request)
        except Exception as exc:
            error = getattr(exc, "response", None)
            if (isinstance(error, dict) and isinstance(error.get("Error"), dict)
                    and error["Error"].get("Code") == "ConditionalCheckFailedException"
                    and isinstance(error.get("ResponseMetadata"), dict)
                    and error["ResponseMetadata"].get("HTTPStatusCode") == 400):
                raise CasConflict() from None
            raise DynamoDbStoreError("DYNAMODB_WRITE_UNCERTAIN", write_uncertain=True) from None
        if not self._ok(response):
            raise DynamoDbStoreError("DYNAMODB_WRITE_UNCERTAIN", write_uncertain=True)
        return version

    def close(self):
        if self._owned_client and self._client is not None:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
