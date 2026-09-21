"""N02-M5: real tiny artificial PCM inputs; no official audio or network.

Run with the existing Python standard library:
  python -B -m unittest discover -s tests/media_pc2 -p test_clova_timeline.py -v

The pinned script is read from a local Git object as original bytes. No fixed
script, shared fixture, media manifest, or production asset is modified.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.media_pc2 import validate_clova_timeline as validator

INTAKE = ROOT / ".local" / "clova-v5-intake"
SCRIPT_REF = "cd262e3425ceaa2710e0d3adc1920a9f87f587c0:planning/media/korean-call-v5-fast-script.json"
SCRIPT_SHA = "47ae253daf158335e92fa136f3e9ba8b3af118fb278b66fcf137e91c3242ade6"
CASE_IDS = ("CASE-0001", "CASE-0002")
OBSERVED_AT = "2026-09-22T00:00:00+09:00"
SOURCE = "Artificial unittest observations; not official CLOVA editor measurements"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def pcm(path: Path, *, frames=8000, width=2, channels=1, rate=8000, value=7) -> None:
    """A real uncompressed WAVE, intentionally tiny and not intelligible speech."""
    sample = value.to_bytes(width, "little", signed=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(width)
        stream.setframerate(rate)
        stream.writeframes(sample * channels * frames)


class ClovaTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_bytes = subprocess.check_output(["git", "show", SCRIPT_REF], cwd=ROOT)
        if len(cls.script_bytes) != 25175 or digest(cls.script_bytes) != SCRIPT_SHA:
            raise AssertionError("Pinned Git script original bytes do not match the M5 card")
        cls.fixed = json.loads(cls.script_bytes)
        INTAKE.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="unittest-", dir=INTAKE)
        self.addCleanup(self.temp.cleanup)
        self.prepare_inputs(Path(self.temp.name))

    def prepare_inputs(self, run):
        """Populate only a caller-created fresh run with artificial input bytes."""
        self.run = run
        self.inputs = self.run / "inputs"
        self.inputs.mkdir()
        self.script = self.inputs / "fixed-script.json"
        self.script.write_bytes(self.script_bytes)
        self.wavs = {case_id: self.inputs / (case_id + ".wav") for case_id in CASE_IDS}
        pcm(self.wavs[CASE_IDS[0]], frames=8000, value=7)
        pcm(self.wavs[CASE_IDS[1]], frames=8800, value=11)
        self.observations = self.inputs / "observations.json"
        self.expected = self.inputs / "expected.json"
        self.output = self.run / "out"
        self.obs = {
            "schemaVersion": "clova-timeline-observations-v1", "origin": "artificial",
            "source": SOURCE, "observedAt": OBSERVED_AT, "uiResolutionSeconds": 0.01,
            "cases": [],
        }
        for case in self.fixed["cases"]:
            turns = []
            for index, turn in enumerate(case["turns"]):
                turns.append({key: turn[key] for key in ("id", "speaker", "text", "spokenText")})
                turns[-1].update(editorInputText=turn["spokenText"], startSeconds=index / 10,
                                 officialGapAfterSeconds=None if index == 9 else 0.01,
                                 gapObservationStatus="not_displayed" if index == 9 else "observed")
            self.obs["cases"].append({"caseId": case["caseId"], "turns": turns})
        self.descriptors = {
            "schemaVersion": "clova-timeline-input-descriptors-v1", "origin": "artificial",
            "script": {"bytes": len(self.script_bytes), "sha256": SCRIPT_SHA},
            "observations": {}, "wavs": [],
        }
        self.sync_inputs()

    def sync_inputs(self):
        """Independent descriptors are refreshed only for deliberately new inputs.

        Corruption tests which target the expected hash explicitly bypass this
        helper after changing that hash or the bound bytes.
        """
        dump(self.observations, self.obs)
        data = self.observations.read_bytes()
        self.descriptors["observations"] = {"bytes": len(data), "sha256": digest(data),
                                               "source": SOURCE, "observedAt": OBSERVED_AT}
        self.descriptors["wavs"] = []
        for case_id, path in self.wavs.items():
            raw = path.read_bytes()
            self.descriptors["wavs"].append({"caseId": case_id, "bytes": len(raw), "sha256": digest(raw)})
        dump(self.expected, self.descriptors)

    def call(self, *, output=None, module=validator, wavs=None):
        return module.validate(script=self.script, wavs=wavs or self.wavs,
                               expected=self.expected, observations=self.observations,
                               output=self.output if output is None else output)

    def current_bytes(self):
        return {str(path): path.read_bytes() for path in
                (self.script, self.expected, self.observations, *self.wavs.values())}

    def assert_report(self, result, status):
        self.assertEqual(result["status"], status, result)
        self.assertIs(result["candidate"], status == "PASS")
        self.assertIs(result["accepted"], False)
        saved = json.loads((self.output / "validation.json").read_bytes())
        self.assertEqual(saved["status"], status)
        self.assertEqual(saved["candidate"], result["candidate"])
        self.assertIs(saved["accepted"], False)
        for name in ("timeline-candidate.json", "fixture-candidate.json"):
            self.assertEqual((self.output / name).exists(), status == "PASS", name)
        if status != "PASS":
            self.assertTrue(result["errors"] or result["unresolved"], result)
            for error in result["errors"]:
                self.assertTrue({"code", "field", "detail"} <= error.keys())

    def reject(self):
        before = self.current_bytes()
        result = self.call()
        self.assert_report(result, "REJECTED")
        self.assertEqual(self.current_bytes(), before)
        return result

    def test_normal_real_pcm_two_cases_and_originals_preserved(self):
        before = self.current_bytes()
        result = self.call()
        self.assert_report(result, "PASS")
        self.assertEqual(self.current_bytes(), before)
        timeline = json.loads((self.output / "timeline-candidate.json").read_bytes())
        fixture = json.loads((self.output / "fixture-candidate.json").read_bytes())
        for payload in (timeline, fixture):
            self.assertIs(payload["accepted"], False)
            self.assertEqual(payload["origin"], "artificial")
        self.assertEqual([c["caseId"] for c in timeline["cases"]], list(CASE_IDS))
        changed_spelling = 0
        for case_index, case in enumerate(timeline["cases"]):
            turns = case["turns"]
            fixed = self.fixed["cases"][case_index]["turns"]
            self.assertEqual(len(turns), 10)
            for i, (actual, expected) in enumerate(zip(turns, fixed)):
                for key in ("id", "speaker", "text", "spokenText"):
                    self.assertEqual(actual[key], expected[key])
                self.assertEqual(actual["startSeconds"], i / 10)
                target_end = ((i + 1) / 10 - 0.01) if i < 9 else (1.0 if case_index == 0 else 1.1)
                self.assertAlmostEqual(actual["endSeconds"], target_end, places=10)
                self.assertLess(actual["startSeconds"], actual["endSeconds"])
                changed_spelling += expected["text"] != expected["spokenText"]
        self.assertEqual(changed_spelling, 5)
        wrong_question = timeline["cases"][1]["turns"][2]
        correction = timeline["cases"][1]["turns"][3]
        self.assertEqual(wrong_question["id"], "F5-W03")
        self.assertEqual(wrong_question["speaker"], "상담원")
        self.assertEqual(correction["id"], "F5-W04")
        self.assertEqual(correction["speaker"], "경영주")

    def test_observed_zero_gap_is_valid(self):
        self.obs["cases"][0]["turns"][0]["officialGapAfterSeconds"] = 0
        self.sync_inputs()
        self.assert_report(self.call(), "PASS")

    def test_last_observed_huge_gap_does_not_reduce_decoded_end(self):
        for case in self.obs["cases"]:
            case["turns"][-1].update(officialGapAfterSeconds=999, gapObservationStatus="observed")
        self.sync_inputs()
        self.assert_report(self.call(), "PASS")
        cases = json.loads((self.output / "timeline-candidate.json").read_bytes())["cases"]
        self.assertEqual([c["turns"][-1]["endSeconds"] for c in cases], [1.0, 1.1])
        self.assertEqual([c["turns"][-1]["officialGapAfterSeconds"] for c in cases], [999, 999])

    def test_middle_null_gap_cannot_borrow_script_pause(self):
        self.obs["cases"][0]["turns"][0].update(officialGapAfterSeconds=None, gapObservationStatus="unresolved")
        self.sync_inputs()
        result = self.reject()
        self.assertTrue(result["unresolved"])

    def test_middle_not_displayed_exception_rejected(self):
        self.obs["cases"][0]["turns"][0].update(officialGapAfterSeconds=None, gapObservationStatus="not_displayed")
        self.sync_inputs()
        self.reject()

    def test_last_null_requires_not_displayed_status(self):
        self.obs["cases"][0]["turns"][-1]["gapObservationStatus"] = "observed"
        self.sync_inputs()
        self.reject()

    def test_case_order_swap_rejected(self):
        self.obs["cases"].reverse()
        self.sync_inputs()
        self.reject()

    def test_duplicate_case_rejected(self):
        self.obs["cases"][1] = copy.deepcopy(self.obs["cases"][0])
        self.sync_inputs()
        self.reject()

    def test_missing_case_rejected(self):
        self.obs["cases"].pop()
        self.sync_inputs()
        self.reject()

    def test_nine_turns_rejected(self):
        self.obs["cases"][0]["turns"].pop()
        self.sync_inputs()
        self.reject()

    def test_eleven_turns_rejected(self):
        self.obs["cases"][0]["turns"].append(copy.deepcopy(self.obs["cases"][0]["turns"][-1]))
        self.sync_inputs()
        self.reject()

    def test_duplicate_turn_id_rejected(self):
        self.obs["cases"][0]["turns"][1]["id"] = self.obs["cases"][0]["turns"][0]["id"]
        self.sync_inputs()
        self.reject()

    def test_turn_order_swapped_rejected(self):
        turns = self.obs["cases"][0]["turns"]
        turns[1], turns[2] = turns[2], turns[1]
        self.sync_inputs()
        self.reject()

    def test_speaker_mismatch_not_automatically_corrected(self):
        self.obs["cases"][1]["turns"][2]["speaker"] = "경영주"
        self.sync_inputs()
        self.reject()

    def test_display_text_mismatch_rejected(self):
        self.obs["cases"][0]["turns"][0]["text"] += " 수정"
        self.sync_inputs()
        self.reject()

    def test_spoken_text_mismatch_rejected(self):
        self.obs["cases"][0]["turns"][0]["spokenText"] += " 수정"
        self.sync_inputs()
        self.reject()

    def test_display_text_cannot_replace_editor_spoken_input(self):
        different = next(t for c in self.obs["cases"] for t in c["turns"] if t["text"] != t["spokenText"])
        different["editorInputText"] = different["text"]
        self.sync_inputs()
        self.reject()

    def test_fixed_script_bytes_cannot_be_reapproved_by_descriptor(self):
        self.script.write_bytes(self.script_bytes + b"\n")
        raw = self.script.read_bytes()
        self.descriptors["script"] = {"bytes": len(raw), "sha256": digest(raw)}
        dump(self.expected, self.descriptors)
        self.reject()

    def test_wrong_expected_wav_sha_rejected(self):
        self.descriptors["wavs"][0]["sha256"] = "0" * 64
        dump(self.expected, self.descriptors)
        self.reject()

    def test_wrong_expected_wav_bytes_rejected(self):
        self.descriptors["wavs"][0]["bytes"] += 1
        dump(self.expected, self.descriptors)
        self.reject()

    def test_case_mapping_does_not_infer_from_filename(self):
        before = self.current_bytes()
        result = self.call(wavs={CASE_IDS[0]: self.wavs[CASE_IDS[1]], CASE_IDS[1]: self.wavs[CASE_IDS[0]]})
        self.assert_report(result, "REJECTED")
        self.assertEqual(self.current_bytes(), before)

    def test_missing_wav_mapping_is_rejected_with_report(self):
        result = self.call(wavs={CASE_IDS[0]: self.wavs[CASE_IDS[0]]})
        self.assert_report(result, "REJECTED")

    def test_duplicate_expected_case_mapping_rejected(self):
        self.descriptors["wavs"][1]["caseId"] = CASE_IDS[0]
        dump(self.expected, self.descriptors)
        self.reject()

    def test_wrong_observation_sha_rejected(self):
        self.descriptors["observations"]["sha256"] = "f" * 64
        dump(self.expected, self.descriptors)
        self.reject()

    def test_observation_origin_mismatch_rejected(self):
        self.obs["origin"] = "official_clova"
        self.sync_inputs()
        self.reject()

    def test_observation_source_mismatch_rejected(self):
        self.obs["source"] = "other source"
        self.sync_inputs()
        self.reject()

    def test_observation_time_mismatch_rejected(self):
        self.obs["observedAt"] = "2026-09-21T01:02:03+09:00"
        self.sync_inputs()
        self.reject()

    def test_empty_observation_source_rejected_even_when_descriptor_agrees(self):
        self.obs["source"] = ""
        self.sync_inputs()
        self.descriptors["observations"]["source"] = ""
        dump(self.expected, self.descriptors)
        self.reject()

    def test_empty_observation_time_rejected_even_when_descriptor_agrees(self):
        self.obs["observedAt"] = ""
        self.sync_inputs()
        self.descriptors["observations"]["observedAt"] = ""
        dump(self.expected, self.descriptors)
        self.reject()

    def test_wrong_observation_schema_rejected(self):
        self.obs["schemaVersion"] = "other-schema"
        self.sync_inputs()
        self.reject()

    def test_wrong_expected_descriptor_schema_rejected(self):
        self.descriptors["schemaVersion"] = "other-schema"
        dump(self.expected, self.descriptors)
        self.reject()

    def test_deep_json_is_rejected_with_safe_validation_report(self):
        base = json.dumps(self.descriptors, ensure_ascii=False)
        # CPython 3.12's C JSON decoder can accept depth 1100 despite the
        # Python recursion limit of 1000; 5000 exercises its actual limit.
        nested = base[:-1] + ',"unknown":' + '[' * 5000 + '0' + ']' * 5000 + '}'
        self.expected.write_text(nested, encoding="utf-8")
        self.reject()

    def test_lone_surrogate_source_rejected_with_matching_descriptor(self):
        self.obs["source"] = "\ud800"
        data = json.dumps(self.obs, ensure_ascii=True).encode("ascii")
        self.observations.write_bytes(data)
        self.descriptors["observations"].update(bytes=len(data), sha256=digest(data), source="\ud800")
        self.expected.write_bytes(json.dumps(self.descriptors, ensure_ascii=True).encode("ascii"))
        result = self.reject()
        self.assertTrue(any(e["code"] == "JSON_UNICODE" for e in result["errors"]))

    def test_duplicate_surrogate_json_key_has_serializable_rejection(self):
        self.expected.write_bytes(b'{"\\ud800":1,"\\ud800":2}')
        result = self.reject()
        self.assertTrue(any(e["code"] == "JSON_DUPLICATE_KEY" for e in result["errors"]))
        # The diagnostic must also be valid output UTF-8, not a second failure.
        (self.output / "validation.json").read_bytes().decode("utf-8")

    def test_expected_bytes_boolean_is_not_integer_measurement(self):
        self.descriptors["wavs"][0]["bytes"] = True
        dump(self.expected, self.descriptors)
        self.reject()

    def test_not_displayed_last_gap_must_remain_null(self):
        self.obs["cases"][0]["turns"][-1]["officialGapAfterSeconds"] = 0
        self.sync_inputs()
        self.reject()

    def test_unobserved_last_and_missing_middle_source_distinguished(self):
        self.obs["cases"][0]["turns"][4]["gapObservationStatus"] = "unresolved"
        self.sync_inputs()
        result = self.reject()
        self.assertTrue(result["unresolved"])

    def test_equal_starts_rejected(self):
        self.obs["cases"][0]["turns"][1]["startSeconds"] = 0
        self.sync_inputs()
        self.reject()

    def test_reverse_starts_rejected(self):
        self.obs["cases"][0]["turns"][4]["startSeconds"] = 0.2
        self.sync_inputs()
        self.reject()

    def test_gap_zero_length_rejected(self):
        self.obs["cases"][0]["turns"][0]["officialGapAfterSeconds"] = 0.1
        self.sync_inputs()
        self.reject()

    def test_decimal_zero_length_gap_rejected(self):
        # 0.4 - 0.1 is 0.30000000000000004 in binary floating point.
        # The declared decimal interval is zero, so this must never pass.
        self.obs["cases"][0]["turns"][3]["officialGapAfterSeconds"] = 0.1
        self.sync_inputs()
        self.reject()

    def test_gap_negative_end_rejected(self):
        self.obs["cases"][0]["turns"][0]["officialGapAfterSeconds"] = 1
        self.sync_inputs()
        self.reject()

    def test_last_start_at_eof_rejected(self):
        self.obs["cases"][0]["turns"][-1]["startSeconds"] = 1.0
        self.sync_inputs()
        self.reject()

    def test_start_past_eof_rejected(self):
        self.obs["cases"][0]["turns"][-1]["startSeconds"] = 1.01
        self.sync_inputs()
        self.reject()

    def test_middle_end_past_eof_rejected(self):
        self.obs["cases"][0]["turns"][-1]["startSeconds"] = 1.2
        self.obs["cases"][0]["turns"][-2]["officialGapAfterSeconds"] = 0
        self.sync_inputs()
        self.reject()

    def test_pcm8_is_unsupported_without_conversion(self):
        pcm(self.wavs[CASE_IDS[0]], width=1)
        self.sync_inputs()
        before = self.current_bytes()
        result = self.call()
        self.assert_report(result, "UNSUPPORTED")
        self.assertEqual(self.current_bytes(), before)

    def test_pcm24_is_unsupported_without_conversion(self):
        pcm(self.wavs[CASE_IDS[0]], width=3)
        self.sync_inputs()
        before = self.current_bytes()
        result = self.call()
        self.assert_report(result, "UNSUPPORTED")
        self.assertEqual(self.current_bytes(), before)

    def test_non_riff_header_rejected(self):
        self.wavs[CASE_IDS[0]].write_bytes(b"NOT-A-WAVE" + b"\0" * 80)
        self.sync_inputs()
        self.reject()

    def test_truncated_data_rejected(self):
        path = self.wavs[CASE_IDS[0]]
        path.write_bytes(path.read_bytes()[:-1])
        self.sync_inputs()
        self.reject()

    def test_frame_alignment_rejected(self):
        fmt = struct.pack("<HHIIHH", 1, 1, 8000, 16000, 2, 16)
        body = b"WAVEfmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", 3) + b"abc\0"
        self.wavs[CASE_IDS[0]].write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
        self.sync_inputs()
        self.reject()

    def test_zero_sample_rate_rejected(self):
        path = self.wavs[CASE_IDS[0]]
        raw = bytearray(path.read_bytes())
        raw[24:28] = struct.pack("<I", 0)
        path.write_bytes(raw)
        self.sync_inputs()
        self.reject()

    def test_inconsistent_riff_size_rejected(self):
        path = self.wavs[CASE_IDS[0]]
        raw = bytearray(path.read_bytes())
        raw[4:8] = struct.pack("<I", len(raw) - 10)
        path.write_bytes(raw)
        self.sync_inputs()
        self.reject()

    def test_zero_frame_wav_rejected(self):
        pcm(self.wavs[CASE_IDS[0]], frames=0)
        self.sync_inputs()
        self.reject()

    def test_stereo_pcm16_is_measured_without_mono_conversion(self):
        pcm(self.wavs[CASE_IDS[0]], channels=2)
        self.sync_inputs()
        before = self.current_bytes()
        self.assert_report(self.call(), "PASS")
        self.assertEqual(self.current_bytes(), before)

    def test_existing_output_directory_is_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "timeline-candidate.json"
        sentinel.write_bytes(b"existing result must stay")
        with self.assertRaises(validator.ValidationError) as error:
            self.call()
        self.assertTrue(error.exception.code)
        self.assertEqual(sentinel.read_bytes(), b"existing result must stay")
        self.assertEqual(list(self.output.iterdir()), [sentinel])

    def test_existing_output_file_is_never_overwritten(self):
        self.output.write_bytes(b"existing output file")
        with self.assertRaises(validator.ValidationError):
            self.call()
        self.assertEqual(self.output.read_bytes(), b"existing output file")

    def test_output_input_collision_rejected(self):
        before = self.current_bytes()
        with self.assertRaises(validator.ValidationError):
            self.call(output=self.inputs)
        self.assertEqual(self.current_bytes(), before)

    def test_output_outside_intake_rejected(self):
        with tempfile.TemporaryDirectory(prefix="clova-output-boundary-", dir=ROOT / ".local") as other:
            outside = Path(other) / "out"
            with self.assertRaises(validator.ValidationError):
                self.call(output=outside)
            self.assertFalse(outside.exists())

    def test_missing_output_parent_rejected(self):
        with self.assertRaises(validator.ValidationError):
            self.call(output=self.run / "absent" / "out")
        self.assertFalse((self.run / "absent").exists())

    def test_hardlinked_input_rejected_and_original_preserved(self):
        original = self.wavs[CASE_IDS[0]]
        alias = self.inputs / "linked.wav"
        os.link(original, alias)
        before = original.read_bytes()
        result = self.call()
        self.assert_report(result, "REJECTED")
        self.assertEqual(alias.read_bytes(), before)
        self.assertEqual(original.read_bytes(), before)

    def test_symlink_input_rejected_if_os_allows_creation(self):
        original = self.wavs[CASE_IDS[0]]
        alias = self.inputs / "symlink.wav"
        try:
            alias.symlink_to(original)
        except OSError as error:
            if getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows denied symlink creation; no security changes attempted")
            raise
        before = original.read_bytes()
        result = self.call(wavs={CASE_IDS[0]: alias, CASE_IDS[1]: self.wavs[CASE_IDS[1]]})
        self.assert_report(result, "REJECTED")
        self.assertEqual(original.read_bytes(), before)

    def test_simulated_junction_attribute_is_rejected(self):
        original_lstat = Path.lstat
        target = self.wavs[CASE_IDS[0]]
        def marked(path):
            info = original_lstat(path)
            if path == target:
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return info
        before = target.read_bytes()
        with patch.object(Path, "lstat", marked):
            result = self.call()
        self.assert_report(result, "REJECTED")
        self.assertTrue(any(e["code"] == "LINK_PATH" for e in result["errors"]))
        self.assertEqual(target.read_bytes(), before)

    def test_input_parent_traversal_is_rejected(self):
        child = self.inputs / "child"
        child.mkdir()
        result = self.call(wavs={CASE_IDS[0]: child / ".." / self.wavs[CASE_IDS[0]].name,
                                CASE_IDS[1]: self.wavs[CASE_IDS[1]]})
        self.assert_report(result, "REJECTED")
        self.assertTrue(any(e["code"] == "UNSAFE_PATH" for e in result["errors"]))

    def test_real_input_bytes_change_during_decode_is_rejected(self):
        target = self.wavs[CASE_IDS[0]]
        original_bytes = target.read_bytes()
        changed_bytes = original_bytes[:-1] + bytes([original_bytes[-1] ^ 1])
        original_inspect = validator.inspect_wav
        def changing(data, field):
            if field == CASE_IDS[0]:
                target.write_bytes(changed_bytes)
            return original_inspect(data, field)
        with patch.object(validator, "inspect_wav", changing):
            result = self.call()
        self.assert_report(result, "REJECTED")
        self.assertTrue(any(e["code"] == "INPUT_CHANGED" for e in result["errors"]))
        self.assertEqual(target.read_bytes(), changed_bytes)  # Validator never repairs/reverts input.

    def test_real_input_identity_replacement_with_same_bytes_is_rejected(self):
        target = self.wavs[CASE_IDS[0]]
        original_bytes, before = target.read_bytes(), target.stat()
        preserved = self.inputs / "preserved-original.wav"
        original_inspect = validator.inspect_wav
        def replacing(data, field):
            if field == CASE_IDS[0]:
                target.rename(preserved)
                target.write_bytes(original_bytes)
                os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            return original_inspect(data, field)
        with patch.object(validator, "inspect_wav", replacing):
            result = self.call()
        self.assert_report(result, "REJECTED")
        self.assertTrue(any(e["code"] == "INPUT_CHANGED" for e in result["errors"]))
        self.assertEqual(target.read_bytes(), original_bytes)
        self.assertEqual(preserved.read_bytes(), original_bytes)
        self.assertNotEqual(target.stat().st_ino, before.st_ino)

    def test_simulated_ctime_only_change_is_rejected(self):
        target = self.wavs[CASE_IDS[0]]
        original_read = validator.read_snapshot
        calls = 0
        def ctime_change(path):
            nonlocal calls
            data, snapshot = original_read(path)
            if Path(path) == target:
                calls += 1
                if calls == 2:
                    snapshot["pathCtimeNs"] += 1
            return data, snapshot
        before = target.read_bytes()
        with patch.object(validator, "read_snapshot", ctime_change):
            result = self.call()
        self.assert_report(result, "REJECTED")
        self.assertTrue(any(e["code"] == "INPUT_CHANGED" for e in result["errors"]))
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(calls, 2)

    def test_mutation_removed_expected_sha_guard_is_detected(self):
        source_path = Path(validator.__file__)
        original_source = source_path.read_bytes()
        source = original_source.decode("utf-8")
        anchor = 'len(raw) == expected["bytes"] and digest(raw) == expected["sha256"]'
        self.assertEqual(source.count(anchor), 1, "Mutation anchor must identify exactly one actual guard")
        # Baseline CONTROL uses the same real decoder and artificial inputs.
        control = self.call(output=self.run / "control")
        self.assertEqual(control["status"], "PASS")
        self.descriptors["wavs"][0]["sha256"] = "0" * 64
        dump(self.expected, self.descriptors)
        self.output = self.run / "baseline-rejected"
        self.assert_report(self.call(), "REJECTED")
        namespace = {"__name__": "isolated_clova_mutant", "__file__": str(source_path)}
        exec(compile(source.replace(anchor, 'len(raw) == expected["bytes"]'),
                     "<isolated expected-SHA mutant>", "exec"), namespace)
        self.output = self.run / "mutant"
        mutated = self.call(module=SimpleNamespace(**namespace))
        self.assertEqual(mutated["status"], "PASS", "Mutant must reach the removed guard's changed behavior")
        # This independent original oracle must actually fail against the mutant.
        with self.assertRaises(AssertionError):
            self.assert_report(mutated, "REJECTED")
        self.assertEqual(source_path.read_bytes(), original_source)

    def test_prepare_artificial_helper_produces_usable_not_run_inputs(self):
        info = prepare_artificial(self.run / "prepared")
        self.assertEqual(info["origin"], "artificial")
        self.assertEqual(info["officialAudio"], {"status": "NOT_RUN", "verified": 0, "total": 2})
        self.assertEqual(info["officialTimeline"], {"status": "NOT_RUN", "verified": 0, "total": 20})
        self.output = Path(info["output"])
        result = validator.validate(Path(info["script"]), {k: Path(v) for k, v in info["wavs"].items()},
                                    Path(info["expected"]), Path(info["observations"]), self.output)
        self.assert_report(result, "PASS")
        self.assertEqual(result["officialAudio"]["status"], "NOT_RUN")
        self.assertEqual(result["officialTimeline"]["status"], "NOT_RUN")

    def test_prepare_artificial_helper_never_reuses_run(self):
        target = self.run / "already"
        target.mkdir()
        sentinel = target / "sentinel"
        sentinel.write_bytes(b"keep this run")
        with self.assertRaises(ValueError):
            prepare_artificial(target)
        self.assertEqual(sentinel.read_bytes(), b"keep this run")
        self.assertEqual(list(target.iterdir()), [sentinel])

    def test_windows_output_rename_during_write_is_blocked(self):
        if os.name != "nt":
            self.skipTest("Windows output directory handle contract")
        original_write = validator.write_new
        blocked = []
        with tempfile.TemporaryDirectory(prefix="clova-rename-target-", dir=ROOT / ".local") as outside:
            escaped = Path(outside) / "escaped-output"
            def race(output, *args, **kwargs):
                try:
                    output.rename(escaped)
                except PermissionError:
                    blocked.append(True)
                return original_write(output, *args, **kwargs)
            with patch.object(validator, "write_new", race):
                result = self.call()
            self.assert_report(result, "PASS")
            self.assertEqual(len(blocked), 3)
            self.assertFalse(escaped.exists())
            self.assertEqual(list(Path(outside).iterdir()), [])


def _bad_numeric_test(field, value):
    def run(self):
        self.obs["cases"][0]["turns"][0][field] = value
        self.sync_inputs()
        self.reject()
    return run


for _field in ("startSeconds", "officialGapAfterSeconds"):
    for _label, _value in (("negative", -0.01), ("bool", True), ("string", "0.01"),
                           ("nan", math.nan), ("infinity", math.inf), ("null", None)):
        setattr(ClovaTimelineTests, "test_invalid_" + _field + "_" + _label,
                _bad_numeric_test(_field, _value))


def prepare_artificial(destination):
    """Explicit CLI helper: never overwrite and never label inputs official."""
    ClovaTimelineTests.setUpClass()
    run = validator.checked_path(destination)
    root = validator.checked_path(INTAKE)
    if run == root or not run.is_relative_to(root) or not run.parent.is_dir() or os.path.lexists(run):
        raise ValueError("Choose a nonexistent new run with an existing parent under .local/clova-v5-intake")
    run.mkdir(exist_ok=False)
    builder = ClovaTimelineTests()
    builder.prepare_inputs(run)
    return {"status": "ARTIFICIAL_INPUTS_PREPARED", "origin": "artificial",
            "officialAudio": {"status": "NOT_RUN", "verified": 0, "total": 2},
            "officialTimeline": {"status": "NOT_RUN", "verified": 0, "total": 20},
            "run": str(run), "script": str(builder.script),
            "wavs": {key: str(value) for key, value in builder.wavs.items()},
            "expected": str(builder.expected), "observations": str(builder.observations),
            "output": str(builder.output)}


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--prepare-artificial":
        print(json.dumps(prepare_artificial(Path(sys.argv[2])), ensure_ascii=False, indent=2))
    else:
        unittest.main(verbosity=2)
