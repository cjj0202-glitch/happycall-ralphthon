"""Negative controls for cross-case, key/time and media interval contamination."""
import copy
import unittest

from media_contract import build_candidates, read_fixture, validate_overlay, SECONDS, FPS, WIDTH, HEIGHT


class MediaContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = read_fixture()
        candidates, missing = build_candidates(self.fixture)
        for item in candidates:
            item.update(bytes=1, sha256="0" * 64, validation={"decodedFrames": SECONDS * FPS,
                "distinctSampleFrames": 4, "width": WIDTH, "height": HEIGHT,
                "fps": FPS, "durationSeconds": SECONDS, "codec": "h264"})
        self.overlay = {"schemaVersion": "pc3-wms-media-candidates-v1", "synthetic": True,
                        "integrationStatus": "candidate-not-registered", "mediaCandidates": candidates,
                        "unregistered": missing, "existingRegistrationUnchanged": [
                            {"caseId": case["id"], "media": case.get("media", [])} for case in self.fixture["cases"]]}

    def test_six_distinct_candidates_and_original_registration_unchanged(self):
        before = copy.deepcopy(self.fixture)
        validate_overlay(self.overlay, self.fixture)
        self.assertEqual(len(self.overlay["mediaCandidates"]), 6)
        self.assertEqual(self.fixture, before)
        self.assertEqual(self.fixture["cases"][0]["media"], [])
        self.assertEqual(self.fixture["cases"][1]["media"][0]["eventIds"], ["W-W3"])

    def test_unknown_totes_are_not_filled_from_other_stages(self):
        rows = self.overlay["mediaCandidates"]
        self.assertIsNone(rows[1]["relations"]["toteId"])
        self.assertIsNone(rows[2]["relations"]["toteId"])
        self.assertIsNone(rows[4]["relations"]["toteId"])
        self.assertEqual(rows[3]["relations"]["toteId"], "SYN-TOTE02-A")
        self.assertEqual(rows[5]["relations"]["toteId"], "SYN-TOTE02-B")

    def test_missing_stage_is_explicitly_unregistered(self):
        self.fixture["cases"][0]["wms"]["events"].pop(2)
        candidates, missing = build_candidates(self.fixture)
        self.assertEqual(len(candidates), 5)
        self.assertEqual(missing[0]["eventId"], "W-M3")

    def test_bad_metadata_mutations_rejected(self):
        mutations = {"caseId": "CASE-0002", "system": "TMS", "eventIds": ["W-W1"],
                     "cameraId": "SYN-CAM-02", "synthetic": False, "startSeconds": -1,
                     "endSeconds": SECONDS + 1, "url": "/demo/sorter-demo.mp4",
                     "occurredAt": "2026-09-19T03:30:00+09:00", "sha256": "not-a-hash",
                     "bytes": 0, "registrationStatus": "registered"}
        for field, value in mutations.items():
            with self.subTest(field=field):
                overlay = copy.deepcopy(self.overlay)
                overlay["mediaCandidates"][0][field] = value
                with self.assertRaises(ValueError):
                    validate_overlay(overlay, self.fixture)

    def test_relation_key_mutations_rejected(self):
        for field in ("storeId", "orderId", "businessDate", "toteId", "asOf"):
            with self.subTest(field=field):
                overlay = copy.deepcopy(self.overlay)
                overlay["mediaCandidates"][0]["relations"][field] = "OTHER"
                with self.assertRaises(ValueError):
                    validate_overlay(overlay, self.fixture)

    def test_future_naive_or_conflicting_event_time_rejected(self):
        for value in ("2026-09-19T03:30:00+09:00", "2026-09-18T03:30:00", "2026-09-18T03:31:00+09:00"):
            with self.subTest(value=value):
                fixture = copy.deepcopy(self.fixture)
                fixture["cases"][0]["wms"]["events"][0]["time"] = value
                with self.assertRaises(ValueError):
                    build_candidates(fixture)

    def test_duplicate_id_rejected(self):
        self.overlay["mediaCandidates"][1] = copy.deepcopy(self.overlay["mediaCandidates"][0])
        with self.assertRaises(ValueError):
            validate_overlay(self.overlay, self.fixture)

    def test_existing_registration_mutation_rejected(self):
        overlay = copy.deepcopy(self.overlay)
        overlay["existingRegistrationUnchanged"][1]["media"][0]["eventIds"] = ["W-W1"]
        with self.assertRaises(ValueError):
            validate_overlay(overlay, self.fixture)


if __name__ == "__main__":
    unittest.main()
