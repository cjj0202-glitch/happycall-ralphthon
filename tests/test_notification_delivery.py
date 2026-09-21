"""D3's first offline Bolt: D01/D03/D06/D07 and the same D03 mutation oracle.

Only synthetic snapshots in TemporaryDirectory are read. This verifies the
read_committed boundary supplied by an independent file-backed source, not the
common repository's integration, persistent delivery recovery, or a provider.
Intent construction was compared with server/notifications.py at
296cba500808147046ebc4326e44e1ffc70a8629; no production identifier helper is used.
"""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock
import urllib.request


@contextmanager
def network_trap():
    """Block sockets/DNS and common HTTP entrypoints, preserving only safe counts."""
    attempts = []

    def denied(*_args, **_kwargs):
        attempts.append("network_attempt_blocked")
        raise AssertionError("External network is forbidden in the D3 fixture")

    with ExitStack() as stack:
        for target in (
            "socket.socket", "socket.create_connection", "socket.getaddrinfo",
            "urllib.request.urlopen", "urllib.request.OpenerDirector.open",
            "http.client.HTTPConnection.connect", "http.client.HTTPSConnection.connect",
        ):
            stack.enter_context(mock.patch(target, side_effect=denied))
        yield attempts


with network_trap() as import_network_attempts:
    from server.notification_delivery import DeliveryCoordinator, SyntheticBinding, FakeTransport
if import_network_attempts:
    raise AssertionError("Delivery module attempted network access during import")


def synthetic_intent(case_id="SYN-D3-001", *, revision=1, kind="handoff",
                     channel="teams", role="center", logical_target="SYN-DEPT-A"):
    """Independent 11-field fixture following the fixed phase-one wire contract."""
    if role == "counselor":
        logical_target = case_id
    recipient_ref = role + ":" + hashlib.sha256(logical_target.encode("utf-8")).hexdigest()
    identity = [1, case_id, revision, kind, channel, role, recipient_ref]
    intent_id = hashlib.sha256(json.dumps(
        identity, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return {
        "schemaVersion": 1, "id": intent_id, "caseId": case_id,
        "caseRevision": revision, "kind": kind, "channel": channel,
        "recipientRole": role, "recipientRef": recipient_ref,
        "createdAt": "2026-09-22T07:38:00+09:00", "status": "not_connected",
        "reason": "delivery_not_configured",
    }


def synthetic_binding(intent, suffix="A"):
    return SyntheticBinding(
        binding_id="SYN-BIND-" + suffix, case_id=intent["caseId"],
        recipient_role=intent["recipientRole"], recipient_ref=intent["recipientRef"],
        channel=intent["channel"],
    )


def snapshot(*intents):
    assert intents and len({row["caseId"] for row in intents}) == 1
    return {"id": intents[0]["caseId"],
            "revision": max(row["caseRevision"] for row in intents),
            "notificationOutbox": deepcopy(list(intents))}


class TemporaryCommittedSource:
    """The coordinator can only see the committed file, never the staged file."""

    def __init__(self, directory):
        self.committed = Path(directory) / "committed-synthetic.json"
        self.staged = Path(directory) / "staged-synthetic.json"
        self.committed.write_text("{}", encoding="utf-8")
        self.reads = []

    def stage(self, *snapshots):
        payload = {row["id"]: deepcopy(row) for row in snapshots}
        self.staged.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def commit_staged(self):
        os.replace(self.staged, self.committed)

    def commit(self, *snapshots):
        self.stage(*snapshots)
        self.commit_staged()

    def read_committed(self, case_id):
        self.reads.append(case_id)
        return json.loads(self.committed.read_text(encoding="utf-8")).get(case_id)


class NotificationDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.network_attempts = self.enterContext(network_trap())
        self.directory = self.enterContext(tempfile.TemporaryDirectory(prefix="happycall-d3-"))
        self.source = TemporaryCommittedSource(self.directory)
        self.transport = FakeTransport()
        self.coordinator = DeliveryCoordinator(self.source, self.transport)

    def tearDown(self):
        self.assertEqual(self.network_attempts, [], "Every D3 operation must remain offline")

    def assert_accepted(self, result, intent):
        self.assertEqual(result.intent_id, intent["id"])
        self.assertEqual((result.state, result.reason), ("accepted", "fake_transport_only"))
        self.assertIsInstance(result.delivery_id, str)
        self.assertTrue(result.delivery_id)

    def assert_d03_oracle(self, mode, observations=None):
        """Identical oracle for original, guard-removal mutant, and restored code."""
        with tempfile.TemporaryDirectory(prefix="happycall-d3-oracle-") as directory:
            source = TemporaryCommittedSource(directory)
            transport = FakeTransport()
            coordinator = DeliveryCoordinator(source, transport)
            intent = synthetic_intent()
            if mode in {"staged_only", "replace_failure"}:
                source.stage(snapshot(intent))
            if mode == "replace_failure":
                with mock.patch.object(os, "replace", side_effect=OSError("synthetic replace failure")):
                    with self.assertRaisesRegex(OSError, "synthetic replace failure"):
                        source.commit_staged()
                self.assertEqual(source.committed.read_text(encoding="utf-8"), "{}")
            result = coordinator.deliver(deepcopy(intent), synthetic_binding(intent))
            observed = {"mode": mode, "calls": len(transport.calls),
                        "records": len(coordinator.records), "state": result.state,
                        "reason": result.reason}
            if observations is not None:
                observations.append(observed)
            self.assertEqual(len(transport.calls), 0,
                             "D03: uncommitted intent must never call transport")
            self.assertEqual(coordinator.records, ())
            self.assertEqual((result.state, result.reason),
                             ("not_committed", "stored_intent_not_found"))
            self.assertEqual(result.intent_id, intent["id"])
            self.assertIsNone(result.delivery_id)
            self.assertEqual(source.reads, [intent["caseId"]])
            return observed

    def test_d01_committed_intent_has_exactly_one_fake_acceptance(self):
        intent = synthetic_intent()
        binding = synthetic_binding(intent)
        stored = snapshot(intent)
        sentinel = "SYN-PRIVATE-RAW-TEXT-DO-NOT-PROJECT"
        stored["raw_text"] = sentinel
        self.source.commit(stored)
        before = self.source.committed.read_bytes()
        result = self.coordinator.deliver(deepcopy(intent), binding)
        self.assert_accepted(result, intent)
        self.assertIsInstance(self.transport.calls, tuple)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertIsInstance(self.coordinator.records, tuple)
        self.assertEqual(len(self.coordinator.records), 1)
        record = self.coordinator.records[0]
        self.assertEqual((record.delivery_id, record.intent_id, record.state,
                          record.binding_id, record.channel),
                         (result.delivery_id, intent["id"], "accepted", binding.binding_id, "teams"))
        self.assertEqual(self.source.reads, [intent["caseId"]])
        self.assertEqual(self.source.committed.read_bytes(), before)
        # D01 safe projection only; this does not execute the D11 payload suite.
        self.assertNotIn(sentinel, repr((result, self.transport.calls, self.coordinator.records)))
        with self.assertRaises(FrozenInstanceError):
            result.state = "posted"
        with self.assertRaises(FrozenInstanceError):
            binding.active = False

    def test_d03_pending_or_failed_commit_never_creates_a_delivery(self):
        for mode in ("candidate_only", "staged_only", "replace_failure"):
            with self.subTest(mode=mode):
                self.assert_d03_oracle(mode)
        with self.subTest(mode="committed_read_unavailable"):
            # A failed read does not establish that an already committed intent
            # is absent. This is D03's source boundary, not a send timeout test.
            intent = synthetic_intent()
            self.source.commit(snapshot(intent))
            committed_before = self.source.committed.read_bytes()
            sentinel = "SYN-PRIVATE-SOURCE-ERROR-DETAIL"
            with mock.patch.object(self.source, "read_committed",
                                   side_effect=OSError(sentinel)):
                result = self.coordinator.deliver(deepcopy(intent), synthetic_binding(intent))
            self.assertEqual((result.state, result.reason),
                             ("blocked", "committed_read_failed"))
            self.assertEqual(result.intent_id, intent["id"])
            self.assertIsNone(result.delivery_id)
            self.assertEqual(self.transport.calls, ())
            self.assertEqual(self.coordinator.records, ())
            self.assertNotIn(sentinel, repr(result))
            self.assertEqual(self.source.committed.read_bytes(), committed_before)

    def test_d06_rediscovery_is_single_send_and_binding_change_is_blocked(self):
        intent = synthetic_intent()
        self.source.commit(snapshot(intent))
        first = self.coordinator.deliver(deepcopy(intent), synthetic_binding(intent))
        self.assert_accepted(first, intent)
        for _ in range(3):
            again = self.coordinator.deliver(deepcopy(intent), synthetic_binding(intent))
            self.assertEqual(again.delivery_id, first.delivery_id)
        original_calls, original_records = self.transport.calls, self.coordinator.records
        self.assertEqual((len(original_calls), len(original_records)), (1, 1))
        blocked = self.coordinator.deliver(deepcopy(intent), synthetic_binding(intent, "REASSIGNED"))
        self.assertEqual((blocked.state, blocked.reason), ("blocked", "binding_changed"))
        self.assertEqual(self.transport.calls, original_calls)
        self.assertEqual(self.coordinator.records, original_records)
        self.assertEqual(self.coordinator.records[0].binding_id, "SYN-BIND-A")

    def test_d07_distinct_cases_recipients_and_channels_stay_separate(self):
        counselor = synthetic_intent("SYN-D3-FINAL", revision=2,
                                     kind="final_reply", role="counselor")
        owner = synthetic_intent("SYN-D3-FINAL", revision=2, kind="final_reply",
                                 channel="kakao", role="owner", logical_target="SYN-STORE-A")
        center = synthetic_intent("SYN-D3-OTHER", logical_target="SYN-DEPT-B")
        intents = (counselor, owner, center)
        self.source.commit(snapshot(counselor, owner), snapshot(center))
        results = [self.coordinator.deliver(deepcopy(row), synthetic_binding(row, str(index)))
                   for index, row in enumerate(intents)]
        for result, row in zip(results, intents):
            self.assert_accepted(result, row)
        self.assertEqual(len({result.delivery_id for result in results}), 3)
        self.assertEqual(len(self.transport.calls), 3)
        self.assertEqual(len(self.coordinator.records), 3)
        self.assertEqual({(row.intent_id, row.binding_id, row.channel, row.state)
                          for row in self.coordinator.records},
                         {(row["id"], "SYN-BIND-" + str(index), row["channel"], "accepted")
                          for index, row in enumerate(intents)})
        # A rediscovery of one recipient must not resend either of the others.
        before = self.transport.calls
        self.coordinator.deliver(deepcopy(owner), synthetic_binding(owner, "1"))
        self.assertEqual(self.transport.calls, before)

    def test_d03_commit_guard_mutation_is_detected_and_original_is_restored(self):
        observations = []
        original_guard = DeliveryCoordinator._committed_intent
        self.assert_d03_oracle("replace_failure", observations)
        with mock.patch.object(DeliveryCoordinator, "_committed_intent",
                               lambda _self, candidate: deepcopy(candidate)):
            with self.assertRaisesRegex(AssertionError,
                                        "D03: uncommitted intent must never call transport"):
                self.assert_d03_oracle("replace_failure", observations)
        self.assertIs(DeliveryCoordinator._committed_intent, original_guard)
        self.assert_d03_oracle("replace_failure", observations)
        self.assertEqual([(row["calls"], row["records"], row["state"])
                          for row in observations],
                         [(0, 0, "not_committed"), (1, 1, "accepted"),
                          (0, 0, "not_committed")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
